"""
Importing this package registers every platform adapter with the registry.
Adding a new platform = write job_hunter/platforms/<name>.py implementing
BaseJobProvider, then add one import line here. Nothing else in the system
needs to change — job_hunter/service.py, routes.py, and scheduler_jobs.py
all go through the registry, never import a specific platform directly.
"""
from job_hunter.platforms import greenhouse   # noqa: F401
from job_hunter.platforms import lever        # noqa: F401
from job_hunter.platforms import ashby        # noqa: F401
from job_hunter.platforms import yc_jobs      # noqa: F401
from job_hunter.platforms import career_pages # noqa: F401
from job_hunter.platforms import internshala  # noqa: F401
from job_hunter.platforms import wellfound    # noqa: F401
