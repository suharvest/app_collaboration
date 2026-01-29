"""
Deployment history persistence service
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings
from ..models.version import DeploymentRecord

logger = logging.getLogger(__name__)


class DeploymentHistory:
    """Persists deployment records to JSON file"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = settings.cache_dir / "deployment_history.json"
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage file exists"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]")

    def _load_records(self) -> List[Dict[str, Any]]:
        """Load all records from storage"""
        try:
            content = self.storage_path.read_text()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load deployment history: {e}")
            return []

    def _save_records(self, records: List[Dict[str, Any]]):
        """Save records to storage"""
        try:
            # Keep only last 1000 records to prevent unbounded growth
            records = records[-1000:]
            content = json.dumps(records, indent=2, default=str)
            self.storage_path.write_text(content)
        except Exception as e:
            logger.error(f"Failed to save deployment history: {e}")

    async def record_deployment(self, record: DeploymentRecord):
        """Record a deployment"""
        try:
            records = self._load_records()
            record_dict = record.model_dump()
            # Convert datetime to ISO string
            if isinstance(record_dict.get("deployed_at"), datetime):
                record_dict["deployed_at"] = record_dict["deployed_at"].isoformat()
            records.append(record_dict)
            self._save_records(records)
            logger.info(
                f"Recorded deployment: {record.deployment_id} for {record.solution_id}/{record.device_id}"
            )
        except Exception as e:
            logger.error(f"Failed to record deployment: {e}")

    async def remove_deployment(self, deployment_id: str) -> bool:
        """Remove a deployment record by deployment_id"""
        try:
            records = self._load_records()
            original_len = len(records)
            records = [r for r in records if r.get("deployment_id") != deployment_id]
            if len(records) < original_len:
                self._save_records(records)
                logger.info(f"Removed deployment record: {deployment_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove deployment: {e}")
            return False

    async def get_history(
        self,
        solution_id: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[DeploymentRecord]:
        """Get deployment history, optionally filtered"""
        try:
            records = self._load_records()

            # Filter by solution_id
            if solution_id:
                records = [r for r in records if r.get("solution_id") == solution_id]

            # Filter by device_id
            if device_id:
                records = [r for r in records if r.get("device_id") == device_id]

            # Sort by deployed_at descending
            records.sort(key=lambda r: r.get("deployed_at", ""), reverse=True)

            # Apply limit
            records = records[:limit]

            # Convert to DeploymentRecord objects
            result = []
            for r in records:
                # Parse datetime string
                if isinstance(r.get("deployed_at"), str):
                    try:
                        r["deployed_at"] = datetime.fromisoformat(r["deployed_at"])
                    except ValueError:
                        r["deployed_at"] = datetime.utcnow()
                result.append(DeploymentRecord(**r))

            return result

        except Exception as e:
            logger.error(f"Failed to get deployment history: {e}")
            return []

    async def get_last_deployed_version(
        self,
        solution_id: str,
        device_id: str,
    ) -> Optional[str]:
        """Get the last deployed version for a device"""
        history = await self.get_history(
            solution_id=solution_id,
            device_id=device_id,
            limit=1,
        )
        if history and history[0].status == "completed":
            return history[0].deployed_version
        return None

    async def get_device_deploy_count(
        self,
        solution_id: str,
        device_id: str,
    ) -> int:
        """Get the number of times a device has been deployed"""
        records = self._load_records()
        count = sum(
            1
            for r in records
            if r.get("solution_id") == solution_id
            and r.get("device_id") == device_id
            and r.get("status") == "completed"
        )
        return count

    async def get_solution_stats(self, solution_id: str) -> Dict[str, Any]:
        """Get deployment statistics for a solution"""
        records = self._load_records()
        solution_records = [r for r in records if r.get("solution_id") == solution_id]

        total = len(solution_records)
        successful = sum(1 for r in solution_records if r.get("status") == "completed")
        failed = sum(1 for r in solution_records if r.get("status") == "failed")

        last_deployment = None
        if solution_records:
            solution_records.sort(key=lambda r: r.get("deployed_at", ""), reverse=True)
            if solution_records[0].get("deployed_at"):
                deployed_at = solution_records[0]["deployed_at"]
                if isinstance(deployed_at, str):
                    try:
                        last_deployment = datetime.fromisoformat(deployed_at)
                    except ValueError:
                        pass
                else:
                    last_deployment = deployed_at

        return {
            "total_deployments": total,
            "successful": successful,
            "failed": failed,
            "last_deployment": last_deployment,
        }


# Global instance
deployment_history = DeploymentHistory()
