# Security Notes

This repository is intended to be safe to publish and clone. It does not track live credentials, inbox exports, browser databases, cookies, local profiles, or machine-specific host files.

## Keep local only

- OAuth client JSON files
- refreshed token files
- browser `Login Data`, `Cookies`, `Local State`, and backups
- live `hosts/*.env` files for your own machines
- any mail exports, local SQLite databases, or generated artifacts containing personal data

## Before adapting these packages

- replace all example placeholders with your own local values
- store secrets in local files, keychains, or re-login flows instead of git
- add local ignore rules before creating any machine-specific env or auth files
- review bundled scripts before pointing them at live accounts or infrastructure

## Publication policy

- this repo uses fresh public commits only
- original source repository histories were not reused here
- source packages were sanitized before import
