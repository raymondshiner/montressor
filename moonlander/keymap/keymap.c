#include QMK_KEYBOARD_H
#include "version.h"
#include "i18n.h"
#define MOON_LED_LEVEL LED_LEVEL
#ifndef ZSA_SAFE_RANGE
#define ZSA_SAFE_RANGE SAFE_RANGE
#endif

/* ─────────────────────────────────────────────────────────────────────────────
 * SirLexicon Moonlander layout — sirlexicon-laptop
 * Source of truth: ~/montressor/moonlander/keymap/keymap.c
 *
 * LAYERS
 *   _DEFAULT (0) — Colemak-DH typing
 *   _OTHER   (1) — F-keys, brackets, arrows, focus-window cluster
 *                  held via LT(_OTHER, KC_ENTER) on the right thumb enter
 *   _APPS    (2) — application launchers
 *                  held via MO(_APPS) on right-hand bottom-row inner
 *                  also LT(_APPS, KC_DELETE) on left thumb middle
 *
 * LABELED KEYS (custom names from Oryx)
 *
 * All Hyprland binds live in ~/.config/hypr/hyprland.conf (search for the combo).
 *
 *   _DEFAULT:
 *     Close App    RGUI(KC_C)        sends Cmd+C → Hyprland: smart-close.sh on Super+C
 *     Smith        LGUI(KC_S)        Super+S → kitty Smith (Oryx label says "Watson" — stale, ignore)
 *     Resume       LGUI(LSFT(KC_P))  Super+Shift+P → ~/.local/bin/resume-project (under Smith)
 *     Jarvis       LGUI(KC_J)        Super+J → kitty Jarvis
 *     App Launch   LGUI(KC_R)        Super+R → walker launcher ($menu)
 *     Friday       TD(TD_FRIDAY_HOGAN)  tap → Super+F (Friday); double-tap → Super+H (Hogan)
 *     Quit         LCTL(KC_C)        Ctrl+C  → universal SIGINT (terminal kill)
 *
 *   _APPS:
 *     YNAB         LGUI(KC_B)        Super+B → YNAB Chrome PWA
 *     Bambu        LGUI(LSFT(KC_B))  Super+Shift+B → bambu-studio (green glow, right of YNAB)
 *     Netflix      LGUI(LSFT(KC_N))  Super+Shift+N → Netflix Chrome PWA (red glow, T-spot left half)
 *     Letterboxd   LGUI(LSFT(KC_L))  Super+Shift+L → Letterboxd web-app (dark-blue glow, above Netflix)
 *     Serializd    LGUI(LALT(KC_S))  Super+Alt+S → Serializd web-app (yellow glow, right of Letterboxd)
 *     Disney+      LGUI(LSFT(KC_D))  Super+Shift+D → Disney+ web-app (light-blue glow, below Netflix)
 *     Music        LGUI(KC_M)        Super+M → toggle music overlay (Musicboard+Spotify, green glow, right of Netflix)
 *     TODO         LGUI(KC_T)        Super+T → Todoist
 *     Google       LGUI(KC_G)        Super+G → google-chrome-stable
 *     Tiimo        LGUI(LSFT(KC_T))  Super+Shift+T → Tiimo web-app (white glow, directly below Google)
 *     Obsidian     LGUI(KC_O)        Super+O → obsidian
 *     Amazon       LGUI(KC_A)        Super+A → Amazon Chrome PWA (left pinky/A column, 3 left of Netflix)
 *     Msgs         LGUI(LSFT(KC_M))  Super+Shift+M → Google Messages PWA
 *     Meet         LGUI(LSFT(KC_G))  Super+Shift+G → Google Meet (new meeting) Chrome app
 *
 *   _OTHER:
 *     Focus Left   LGUI(KC_LEFT)     Super+arrows → movefocus
 *     Focus Down   LGUI(KC_DOWN)
 *     Focus Up     LGUI(KC_UP)
 *     Focus Right  LGUI(KC_RIGHT)
 *
 * Skill for adding more: ~/.claude/skills/moonlander-hotkey.md (or /new-hotkey)
 * ───────────────────────────────────────────────────────────────────────── */

enum layers {
  _DEFAULT = 0,
  _OTHER   = 1,
  _APPS    = 2,
};

enum custom_keycodes {
  RGB_SLD = ZSA_SAFE_RANGE,
};

enum tap_dance_codes {
  TD_FRIDAY_HOGAN,
};

// _DEFAULT Friday key: single tap → Super+F (Friday), double tap → Super+H (Hogan)
tap_dance_action_t tap_dance_actions[] = {
  [TD_FRIDAY_HOGAN] = ACTION_TAP_DANCE_DOUBLE(LGUI(KC_F), LGUI(KC_H)),
};


const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
  [_DEFAULT] = LAYOUT_moonlander(
    RGUI(KC_C),     KC_1,           KC_2,           KC_3,           KC_4,           KC_5,           LGUI(KC_S),                                     LGUI(KC_J),     KC_6,           KC_7,           KC_8,           KC_9,           KC_0,           LGUI(KC_R),
    KC_TAB,         KC_Q,           KC_W,           KC_F,           KC_P,           KC_B,           LGUI(LSFT(KC_P)),                               TD(TD_FRIDAY_HOGAN), KC_J,      KC_L,           KC_U,           KC_Y,           KC_SCLN,        KC_BSLS,
    KC_ESCAPE,      KC_A,           KC_R,           KC_S,           KC_T,           KC_G,           KC_EQUAL,                                                                       KC_MINUS,       KC_M,           KC_N,           KC_E,           KC_I,           KC_O,           KC_QUOTE,
    KC_LEFT_SHIFT,  KC_Z,           KC_X,           KC_C,           KC_D,           KC_V,                                           KC_K,           KC_H,           KC_COMMA,       KC_DOT,         KC_SLASH,       KC_RIGHT_SHIFT,
    KC_LEFT_CTRL,   KC_LEFT_ALT,    KC_PC_CUT,      KC_PC_COPY,     KC_PC_PASTE,    KC_LEFT_GUI,                                                                                                    MO(_APPS),      KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_SPACE,       KC_BSPC,        LT(_APPS, KC_DELETE),                            LCTL(KC_C),     KC_BSPC,        LT(_OTHER, KC_ENTER)
  ),

  [_OTHER] = LAYOUT_moonlander(
    KC_TRANSPARENT, KC_F1,          KC_F2,          KC_F3,          KC_F4,          KC_F5,          KC_F11,                                         KC_F12,         KC_F6,          KC_F7,          KC_F8,          KC_F9,          KC_F10,         KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, LGUI(KC_LEFT),  LGUI(KC_DOWN),  LGUI(KC_UP),    LGUI(KC_RIGHT), KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_GRAVE,       KC_LCBR,        KC_LBRC,        KC_LPRN,        KC_TRANSPARENT, KC_TRANSPARENT,                                                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_RPRN,        KC_RBRC,        KC_RCBR,        KC_PIPE,        KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_LEFT,        KC_DOWN,        KC_UP,          KC_RIGHT,       KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                                                                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT
  ),

  [_APPS] = LAYOUT_moonlander(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, LGUI(LSFT(KC_L)), LGUI(LALT(KC_S)), KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, LGUI(KC_B),     LGUI(LSFT(KC_B)), KC_TRANSPARENT, LGUI(LSFT(KC_G)),KC_TRANSPARENT,
    KC_TRANSPARENT, LGUI(KC_A),     KC_TRANSPARENT, KC_TRANSPARENT, LGUI(LSFT(KC_N)), LGUI(KC_M),     KC_TRANSPARENT,                                                                 KC_TRANSPARENT, LGUI(KC_T),     LGUI(KC_G),     LGUI(KC_O),     KC_TRANSPARENT, LGUI(LSFT(KC_M)),KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, LGUI(LSFT(KC_D)), KC_TRANSPARENT,                                 KC_TRANSPARENT, LGUI(LSFT(KC_T)), KC_TRANSPARENT, KC_TRANSPARENT,  KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                                                                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT
  ),
};




extern rgb_config_t rgb_matrix_config;

RGB hsv_to_rgb_with_value(HSV hsv) {
  RGB rgb = hsv_to_rgb( hsv );
  float f = (float)rgb_matrix_config.hsv.v / UINT8_MAX;
  return (RGB){ f * rgb.r, f * rgb.g, f * rgb.b };
}

void keyboard_post_init_user(void) {
  rgb_matrix_enable();
}

const uint8_t PROGMEM ledmap[][RGB_MATRIX_LED_COUNT][3] = {
    [_DEFAULT] = { {253,255,255}, {46,255,255}, {253,255,255}, {46,255,255}, {46,255,255}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {46,255,255}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {200,255,255}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {200,255,255}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {200,255,255}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {0,0,255}, {0,0,255}, {26,255,255}, {46,255,255}, {253,255,255}, {253,255,255}, {0,0,255}, {218,255,255}, {26,255,255}, {26,255,255}, {46,255,255}, {0,0,0}, {96,255,255}, {26,255,255}, {139,255,255}, {26,255,255}, {0,0,0}, {96,255,255}, {139,255,255}, {139,255,255}, {26,255,255}, {0,0,0}, {96,255,255}, {139,255,255}, {139,255,255}, {26,255,255}, {0,0,0}, {96,255,255}, {139,255,255}, {139,255,145}, {139,255,255}, {0,0,0}, {96,255,255}, {139,255,255}, {139,255,255}, {139,255,255}, {0,0,255}, {0,0,255}, {26,255,255}, {46,255,255}, {253,255,255}, {253,255,255}, {218,255,255} },

    [_OTHER] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {10,225,255}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {10,225,255}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {10,225,255}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {10,225,255}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {128,255,255}, {0,0,0}, {10,225,255}, {0,0,0}, {0,0,0}, {128,255,255}, {141,255,255}, {10,225,255}, {214,255,255}, {0,0,0}, {128,255,255}, {141,255,255}, {10,225,255}, {214,255,255}, {0,0,0}, {128,255,255}, {141,255,255}, {10,225,255}, {214,255,255}, {0,0,0}, {128,255,255}, {141,255,255}, {0,0,0}, {214,255,255}, {128,255,255}, {0,0,0}, {0,0,0}, {109,255,255}, {0,0,0}, {0,0,0}, {0,0,0} },

    [_APPS] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {172,255,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {170,255,200}, {0,255,255}, {150,170,255}, {0,0,0}, {0,0,0}, {43,255,255}, {90,255,150}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {187,113,234}, {0,0,0}, {0,0,0}, {0,0,0}, {40,255,255}, {139,135,212}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,255}, {0,0,0}, {0,0,0}, {85,255,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {139,243,243}, {23,243,221}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,218,204}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },

};

void set_layer_color(int layer) {
  for (int i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    HSV hsv = {
      .h = pgm_read_byte(&ledmap[layer][i][0]),
      .s = pgm_read_byte(&ledmap[layer][i][1]),
      .v = pgm_read_byte(&ledmap[layer][i][2]),
    };
    if (!hsv.h && !hsv.s && !hsv.v) {
        rgb_matrix_set_color( i, 0, 0, 0 );
    } else {
        RGB rgb = hsv_to_rgb_with_value(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
  }
}

bool rgb_matrix_indicators_user(void) {
  if (rawhid_state.rgb_control) {
      return false;
  }
  if (!keyboard_config.disable_layer_led) {
    switch (biton32(layer_state)) {
      case _DEFAULT:
        set_layer_color(_DEFAULT);
        break;
      case _OTHER:
        set_layer_color(_OTHER);
        break;
      case _APPS:
        set_layer_color(_APPS);
        break;
     default:
        if (rgb_matrix_get_flags() == LED_FLAG_NONE) {
          rgb_matrix_set_color_all(0, 0, 0);
        }
    }
  } else {
    if (rgb_matrix_get_flags() == LED_FLAG_NONE) {
      rgb_matrix_set_color_all(0, 0, 0);
    }
  }

  return true;
}




bool process_record_user(uint16_t keycode, keyrecord_t *record) {
  switch (keycode) {

    case RGB_SLD:
        if (rawhid_state.rgb_control) {
            return false;
        }
        if (record->event.pressed) {
            rgblight_mode(1);
        }
        return false;
  }
  return true;
}
