# Security policy

Maverick Bank 0.1.0 is a release candidate. No security audit, response-time commitment or public vulnerability-reporting service is claimed.

For a suspected vulnerability, contact the person who supplied your build privately. This candidate has no established public repository or dedicated security inbox. Do not publish memory contents, client configuration, credentials or personal paths in a report. Share a minimal reproduction using a temporary bank with invented data, the package version, operating system, command and redacted error.

Treat path escape, unintended network transfer, arbitrary execution, interference with unrelated Git repositories and loss of authoritative notes/history as security-relevant. Ordinary model disagreement or an incorrect saved claim is not evidence of a software vulnerability, though it may reveal a product defect.

Use a private local directory. Notes, indexes, embeddings, journals, backups and Git history are not encrypted. A process running as your user can access them; scopes are retrieval labels, not access controls. Host agents can forward retrieved text to their model providers. See [privacy and threat boundary](docs/PRIVACY.md).

Do not paste secrets into a diagnostic report. Removing text from a note does not erase old Git snapshots or external backups. If a credential was stored, revoke it first and review all copies separately.
