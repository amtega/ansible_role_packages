# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.18.0] - 2022-06-09
### Changed
- Migrated tests to podman
- Moved dependencies to include file to avoid race conditions with hosts vars.

### Fixed
- Fixed typo.

## [1.17.0] - 2022-02-16
### Changed
- Adapted for CentOS derived distros. Related to ansible/main#263

## [1.16.1] - 2022-02-11
### Changed
- Changed testing images.

## [1.16.0] - 2022-01-26
### Changed
- Supported distros. Related to ansible/main#178

### [1.15.0] - 2021-11-08
### Added
- Added support for `disable_gpg_check` in operating systems packages.
