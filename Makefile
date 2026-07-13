# Local image defaults (see README: hub.docker.com/r/harrykodden/scim)
IMAGE ?= scim-sample
DOCKER_IMAGE ?= harrykodden/scim
REPOSITORY_URL ?= harrykodden
ARCHITECTURE ?= linux/amd64
TAG ?= latest
VERSION ?=

SEMVER_RE = ^[0-9]+\.[0-9]+\.[0-9]+$$

.PHONY: all build develop push help version release release-check release-draft _resolve-version

help:
	@echo "Targets:"
	@echo "  make build              Build image locally ($(IMAGE):$(TAG))"
	@echo "  make develop            Run dev server with hot reload"
	@echo "  make push               Build and push $(DOCKER_IMAGE):$(TAG)"
	@echo "  make version            Show latest tag and next auto-bumped version"
	@echo "  make release            Create GitHub release (bumps minor from latest tag)"
	@echo "  make release VERSION=x.y.z   Create release with an explicit version"
	@echo "  make release-draft      Create draft GitHub release (same version rules)"
	@echo ""
	@echo "Release flow:"
	@echo "  1. Merge changes to main and ensure CI is green"
	@echo "  2. make release          # e.g. v1.2.3 -> v1.3.0"
	@echo "  3. GitHub Actions publishes $(DOCKER_IMAGE):<version>, :<major>.<minor>, :<major>, and :latest"

# Prints the release version (stdout). Honors VERSION= override; otherwise bumps minor.
_resolve-version:
	@if [ -n "$(VERSION)" ]; then echo "$(VERSION)"; exit 0; fi; \
	git fetch --tags --quiet 2>/dev/null || true; \
	last=$$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1 | sed 's/^v//'); \
	if [ -z "$$last" ]; then echo "1.0.0"; \
	else \
	  major=$$(echo $$last | cut -d. -f1); \
	  minor=$$(echo $$last | cut -d. -f2); \
	  echo "$$major.$$((minor+1)).0"; \
	fi

version:
	@git fetch --tags --quiet 2>/dev/null || true; \
	last=$$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1); \
	next=$$($(MAKE) -s _resolve-version); \
	if [ -z "$$last" ]; then \
	  echo "Latest: (none)"; \
	  echo "Next release: $$next"; \
	else \
	  echo "Latest: $$last"; \
	  echo "Next release: $$next"; \
	fi

release-check:
	@VERSION=$$($(MAKE) -s _resolve-version); \
	echo "$$VERSION" | grep -Eq "$(SEMVER_RE)" || (echo "VERSION must be semver (x.y.z), got: $$VERSION"; exit 1); \
	command -v gh >/dev/null 2>&1 || (echo "Install GitHub CLI: https://cli.github.com/"; exit 1); \
	test -z "$$(git status --porcelain)" || (echo "Working tree is not clean; commit or stash changes first"; exit 1); \
	! git rev-parse "v$$VERSION" >/dev/null 2>&1 || (echo "Tag v$$VERSION already exists"; exit 1); \
	echo "Ready to publish v$$VERSION -> $(DOCKER_IMAGE):$$VERSION"

release: release-check
	@VERSION=$$($(MAKE) -s _resolve-version); \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--generate-notes; \
	echo ""; \
	echo "Published v$$VERSION."; \
	echo "Watch: https://github.com/$$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/workflows/release.yml"; \
	echo "Images: $(DOCKER_IMAGE):$$VERSION, $(DOCKER_IMAGE):latest"

release-draft: release-check
	@VERSION=$$($(MAKE) -s _resolve-version); \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--generate-notes \
		--draft; \
	echo "Draft release v$$VERSION created. Publish it on GitHub to build Docker images."

build all:
	docker build \
		--platform "$(ARCHITECTURE)" \
		. \
		-t $(IMAGE) \
		-t $(IMAGE):$(TAG) \
		-t $(REPOSITORY_URL)/$(IMAGE):$(TAG)

develop: build
	docker \
		run --rm \
		--name scim \
		--network host \
		-v $$PWD:/app \
		-e LOGLEVEL=INFO \
		-e PYTHONPATH=/app \
		-e SCHEMA_PATH=/app/schemas \
		--entrypoint /usr/local/bin/uvicorn \
		$(IMAGE) main:app --reload --host 0.0.0.0 --port 8888

push: build
	docker push $(REPOSITORY_URL)/$(IMAGE):$(TAG)
