COMPONENT := custom_components/vrcx4
VERSION := $(shell python3 -c "import json; print(json.load(open('$(COMPONENT)/manifest.json'))['version'])")
BRAND := $(COMPONENT)/brand
ICON_SVG := assets/icon.svg

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

.PHONY: version
version: ## Print the manifest version
	@echo $(VERSION)

.PHONY: brand
brand: ## Rasterize HACS brand images (icon/logo @1x and @2x) from $(ICON_SVG)
	@command -v rsvg-convert >/dev/null || { echo "need rsvg-convert (brew install librsvg)"; exit 1; }
	@mkdir -p $(BRAND)
	rsvg-convert -w 256 -h 256 $(ICON_SVG) -o $(BRAND)/icon.png
	rsvg-convert -w 512 -h 512 $(ICON_SVG) -o $(BRAND)/icon@2x.png
	rsvg-convert -w 256 -h 256 $(ICON_SVG) -o $(BRAND)/logo.png
	rsvg-convert -w 512 -h 512 $(ICON_SVG) -o $(BRAND)/logo@2x.png
	@command -v magick >/dev/null && for f in $(BRAND)/*.png; do magick "$$f" -strip "$$f"; done || true
	@echo "brand images written to $(BRAND)"

.PHONY: check
check: ## Validate JSON manifests, brand images, and byte-compile the component
	@python3 -m json.tool $(COMPONENT)/manifest.json >/dev/null && echo "manifest.json ok"
	@python3 -m json.tool hacs.json >/dev/null && echo "hacs.json ok"
	@for f in icon.png icon@2x.png logo.png logo@2x.png; do \
		test -f $(BRAND)/$$f || { echo "missing $(BRAND)/$$f (run 'make brand')"; exit 1; }; \
	done && echo "brand images ok"
	@python3 -m compileall -q $(COMPONENT) && echo "compile ok"

.PHONY: release
release: check ## Tag the manifest version and publish a GitHub release (gh)
	@git diff --quiet HEAD || { echo "working tree dirty — commit first"; exit 1; }
	@git rev-parse "v$(VERSION)" >/dev/null 2>&1 && { echo "tag v$(VERSION) already exists"; exit 1; } || true
	git push
	gh release create "v$(VERSION)" --title "v$(VERSION)" --generate-notes
	@echo "released v$(VERSION)"
