##############################################
#### Automatic Pythonic Developer Experience ##
##############################################
##
## If you don't really know what to do, run `make help`.
##

## Image coordinates
REGISTRY   ?= ghcr.io
NAMESPACE  ?= samhclark
IMAGE_NAME ?= custom-silverblue
TAG        ?= 44

## Tool variables (override on the command line, e.g. make build PODMAN=buildah)
PYTHON ?= python3
UVX    ?= uvx
PODMAN ?= podman

RUFF ?= $(UVX) ruff
TY   ?= $(UVX) ty

## Colors
COLOR_BLUE  = \033[34m
COLOR_GREEN = \033[32m
COLOR_RED   = \033[31m
COLOR_RESET = \033[0m

###
### TASKS
###

.DEFAULT_GOAL := all

##@ Default

.PHONY: all
all: deps check test build ## Run deps, check, test, and build (default)

##@ Utility

.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

.PHONY: check
check: check-ruff-format check-ruff-lint check-ty ## Run all checks

.PHONY: check-ruff-format
check-ruff-format: ## Check code formatting with ruff
	$(RUFF) format --check .

.PHONY: check-ruff-lint
check-ruff-lint: ## Run ruff linter
	$(RUFF) check $(RUFF_CHECK_OPTS) . || \
		(printf "$(COLOR_RED)Run 'make format' to fix some issues, then 'make check' again.$(COLOR_RESET)\n" && false)

RUFF_CHECK_OPTS ?=
.PHONY: check-ruff-fix
check-ruff-fix: ## Run ruff linter with automatic fixes
	$(MAKE) check-ruff-lint RUFF_CHECK_OPTS=--fix

.PHONY: check-ty
check-ty: ## Run ty type checker
	$(TY) check .

.PHONY: format
format: ## Auto-format code with ruff (makes changes in place)
	$(RUFF) format .

.PHONY: test
test: ## Run unit tests
	cd secret-run && $(PYTHON) -m unittest test_secret_run -v
	@printf "$(COLOR_GREEN)test succeeded$(COLOR_RESET)\n"

##@ Building and Publishing

.PHONY: build
build: ## Build the bootc container image
	$(PODMAN) build --file Containerfile --tag $(IMAGE_NAME):$(TAG) --signature-policy overlay-root/etc/containers/policy.json .
	@printf "$(COLOR_GREEN)build succeeded: $(IMAGE_NAME):$(TAG)$(COLOR_RESET)\n"

.PHONY: publish
publish: ## Push the container image to the registry (requires prior login)
	$(PODMAN) push $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(TAG)
	@printf "$(COLOR_GREEN)publish succeeded: $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(TAG)$(COLOR_RESET)\n"

##@ Dependencies

.PHONY: deps
deps: deps-check-uv deps-check-podman ## Check that required tools are available
	@printf "$(COLOR_GREEN)All deps present!$(COLOR_RESET)\n"

.PHONY: deps-check-uv
deps-check-uv: ## Check that uv is available (install via https://docs.astral.sh/uv/getting-started/installation/)
	@command -v uv > /dev/null || \
		(printf "$(COLOR_RED)uv not found. Install it: curl -LsSf https://astral.sh/uv/install.sh | sh$(COLOR_RESET)\n" && false)
	@printf "$(COLOR_BLUE)uv: $$(uv --version)$(COLOR_RESET)\n"

.PHONY: deps-check-podman
deps-check-podman: ## Check that podman is available
	@command -v $(PODMAN) > /dev/null || \
		(printf "$(COLOR_RED)$(PODMAN) not found. Install it via your system package manager.$(COLOR_RESET)\n" && false)
	@printf "$(COLOR_BLUE)podman: $$($(PODMAN) --version)$(COLOR_RESET)\n"

##@ Updates

GOOGLE_SIGNING_KEY_URL ?= https://dl.google.com/linux/linux_signing_key.pub

.PHONY: update-keys
update-keys: update-key-google ## Update vendor GPG keys from upstream sources

.PHONY: update-key-google
update-key-google: ## Fetch the latest Google Linux signing key
	curl -fsSL $(GOOGLE_SIGNING_KEY_URL) -o overlay-root/etc/pki/rpm-gpg/google-linux-public-key.asc
	@printf "$(COLOR_GREEN)Google signing key updated$(COLOR_RESET)\n"

##@ Cleanup

.PHONY: clean
clean: ## Remove Python caches and build artifacts
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	find . -name .ruff_cache -type d -prune -exec rm -rf {} +
	find . -name .ty_cache  -type d -prune -exec rm -rf {} +
	@printf "$(COLOR_GREEN)Clean!$(COLOR_RESET)\n"
