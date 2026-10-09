# Contributing to Meeting Minutes

Use Python 3.11+ and Node 22+. Follow README local setup and run the backend tests, extraction diagnostic, frontend build and frontend tests before submitting a PR. Keep transcript fixtures synthetic and model requests mocked. Never commit credentials, real meeting transcripts, databases or generated dependencies.

Changes to citation offsets, date rules, approvals or exports need behavior tests, including invalid inputs and failure paths. Preserve optimistic revision checks and independent reviewer separation. OIDC changes need signed-token and browser-state tests. Describe user-visible changes and validation in the PR; preserve existing attribution and the MIT license.

Alan Vo — alanvo@gmail.com
