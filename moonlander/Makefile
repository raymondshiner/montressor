KEYMAP_NAME := sirlexicon
# Moonlander has two hardware revisions: reva (original) and revb (newer).
# Confirmed reva from the Oryx source export filename on 2026-06-12.
KB          := zsa/moonlander/reva
QMK_HOME    := $(HOME)/qmk_firmware
# Keymaps are shared across revisions — live at the parent moonlander/keymaps/ dir.
KEYMAP_DIR  := $(QMK_HOME)/keyboards/zsa/moonlander/keymaps/$(KEYMAP_NAME)
SRC_KEYMAP  := $(CURDIR)/keymap
# QMK names built bins with underscores: zsa_moonlander_<rev>_<keymap>.bin
KB_FILESAFE := $(subst /,_,$(KB))
BUILT_BIN   := $(QMK_HOME)/$(KB_FILESAFE)_$(KEYMAP_NAME).bin
OUT_BIN     := $(CURDIR)/firmware/$(KEYMAP_NAME).bin

.PHONY: link compile flash all clean status

link:
	@mkdir -p $(dir $(KEYMAP_DIR))
	@if [ -e "$(KEYMAP_DIR)" ] && [ ! -L "$(KEYMAP_DIR)" ]; then \
		echo "ERROR: $(KEYMAP_DIR) exists and is not a symlink. Remove it first."; exit 1; \
	fi
	@ln -sfn $(SRC_KEYMAP) $(KEYMAP_DIR)
	@echo "linked $(KEYMAP_DIR) -> $(SRC_KEYMAP)"

compile: link
	cd $(QMK_HOME) && qmk compile -kb $(KB) -km $(KEYMAP_NAME)
	@mkdir -p firmware
	@cp $(BUILT_BIN) $(OUT_BIN) 2>/dev/null || \
	 cp $(QMK_HOME)/.build/$(KB_FILESAFE)_$(KEYMAP_NAME).bin $(OUT_BIN) 2>/dev/null || \
	 (echo "could not locate built .bin at $(BUILT_BIN)"; exit 1)
	@echo "built -> $(OUT_BIN)"

flash: link
	cd $(QMK_HOME) && qmk flash -kb $(KB) -km $(KEYMAP_NAME)
	@mkdir -p firmware
	@cp $(BUILT_BIN) $(OUT_BIN) 2>/dev/null || true
	@echo "flashed: $(OUT_BIN)"

all: compile

clean:
	cd $(QMK_HOME) && qmk clean
	rm -f $(OUT_BIN)

status:
	@echo "QMK_HOME    = $(QMK_HOME)"
	@echo "KEYMAP_DIR  = $(KEYMAP_DIR)"
	@echo "SRC_KEYMAP  = $(SRC_KEYMAP)"
	@echo "OUT_BIN     = $(OUT_BIN)"
	@echo ""
	@echo "qmk:      $$(qmk --version 2>/dev/null || echo MISSING)"
	@echo "kontroll: $$(kontroll --version 2>/dev/null || echo MISSING)"
	@echo "keymapp:  $$(command -v keymapp >/dev/null && echo present || echo MISSING)"
