import json
import subprocess
from pathlib import Path

secrets_path = Path.home() / ".uspc" / "secrets" / "secrets.json"
admin_pass = "uspc_admin_pass_2026!"
if secrets_path.exists():
    try:
        data = json.loads(secrets_path.read_text(encoding="utf-8"))
        if data.get("nextcloud_admin_password"):
            admin_pass = data["nextcloud_admin_password"]
    except Exception:
        pass

status_res = subprocess.run(
    ["kubectl", "exec", "-n", "uspc", "deployment/nextcloud", "--", "php", "occ", "status"],
    capture_output=True,
    text=True,
)

if "installed: true" in status_res.stdout:
    print("Nextcloud is already installed. Configuring trusted domains...")
else:
    print("==> Initializing Nextcloud in Kubernetes...")
    subprocess.run(
        [
            "kubectl",
            "exec",
            "-n",
            "uspc",
            "deployment/nextcloud",
            "--",
            "rm",
            "-rf",
            "/var/www/html/data/admin",
        ],
        capture_output=True,
    )
    install_cmd = [
        "kubectl",
        "exec",
        "-n",
        "uspc",
        "deployment/nextcloud",
        "--",
        "su",
        "-s",
        "/bin/sh",
        "www-data",
        "-c",
        f"php occ maintenance:install --database=pgsql --database-name=nextcloud --database-host=postgres.uspc.svc.cluster.local --database-user=nextcloud --database-pass=uspc_postgres_secure_pass --admin-user=admin --admin-pass='{admin_pass}' --data-dir=/var/www/html/data",
    ]
    res = subprocess.run(install_cmd, capture_output=True, text=True)
    print("Install stdout:", res.stdout)

# Configure trusted domains
for idx, domain in enumerate(["localhost", "127.0.0.1", "mycloud.local"], start=1):
    domain_cmd = [
        "kubectl",
        "exec",
        "-n",
        "uspc",
        "deployment/nextcloud",
        "--",
        "su",
        "-s",
        "/bin/sh",
        "www-data",
        "-c",
        f"php occ config:system:set trusted_domains {idx} --value={domain}",
    ]
    subprocess.run(domain_cmd, capture_output=True, text=True)

# Create user directories
dir_cmd = [
    "kubectl",
    "exec",
    "-n",
    "uspc",
    "deployment/nextcloud",
    "--",
    "mkdir",
    "-p",
    "/var/www/html/data/admin/files/Documents",
    "/var/www/html/data/admin/files/Photos",
]
subprocess.run(dir_cmd, capture_output=True, text=True)

chown_cmd = [
    "kubectl",
    "exec",
    "-n",
    "uspc",
    "deployment/nextcloud",
    "--",
    "chown",
    "-R",
    "www-data:www-data",
    "/var/www/html/data",
]
subprocess.run(chown_cmd, capture_output=True, text=True)

scan_cmd = [
    "kubectl",
    "exec",
    "-n",
    "uspc",
    "deployment/nextcloud",
    "--",
    "su",
    "-s",
    "/bin/sh",
    "www-data",
    "-c",
    "php occ files:scan --all",
]
scan_res = subprocess.run(scan_cmd, capture_output=True, text=True)
print("Files scan:", scan_res.stdout)
print("==> Nextcloud initialization complete!")
