// ee_fps.dll - first-person shooter mode for Empire Earth (NeoEE build, base game only).
//
// Single player only. Loaded by EE-Cheats.exe (see cheat/ee_cheat.py). Select ONE own ranged unit,
// press the toggle key (default ^) and you see through its eyes: mouse = look, WASD = walk,
// left mouse = shoot at what is under the crosshair, 1/2/3/4 or mouse wheel or Q = weapons,
// ^ or ESC = back to the normal view. The unit becomes a hero (more HP, takes less damage, regenerates,
// range/sight >= 9) and is normalised again when the mode ends (also on death).
//
// Everything that touches the game is in this file; addresses are for the NeoEE "Empire Earth.exe"
// (md5 D531B5F8...) and its EE-Cheats.exe copy. The DLL checks the code bytes before it hooks anything
// and stays passive if they do not match.

#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <share.h>

// ------------------------------------------------------------------ game addresses (exe)
#define G_WORLD       0x918300u   // EEWorld (thiscall this for lookup)
#define G_PLAYERS     0x918374u   // EEPlayer* [9]
#define G_LOCAL       0x918E84u   // local player index
#define G_COMM        0x91984Cu   // comm object, byte +0x2E != 0 -> network game
#define G_CAMOBJ      0x918CD0u   // RTS camera object, look-at x/y at +0x40/+0x44
#define G_CAMCLEAN    0x9128CBu   // byte: 0 = camera changed -> SetCamera + full terrain transform this frame
#define F_LOOKUP      0x53B889u   // EEWorld::GetUnit(id)
#define F_EXEC_SELECT 0x4BCF73u   // EEMSelectUnit::Execute
#define F_EXEC_UNSEL  0x4BF9C7u   // EEMUnselectAllUnits::Execute
#define F_EXEC_ATTACK 0x4B3958u   // EEMAttackUnit::Execute (uses the selection)
#define F_EXEC_PATHTO 0x4B9D7Bu   // EEMPathTo::Execute (uses the selection)
#define F_EXEC_HALT   0x4B73C9u   // EEMHaltSelectedGroup::Execute
#define F_DAMAGE      0x6172BCu   // EEUnit::TakeDamage(this=target, attacker/projectile, int dmg, int, int)
#define F_OPNEW       0x683718u   // operator new (cdecl)
#define F_UCU_CTOR    0x627765u   // EEUnitClassUpgrade::EEUnitClassUpgrade(EEUC* db)
#define F_CHAT_ADD    0x661E91u   // chat display: add line (thiscall, 5 args)
#define G_CHATDISP    0x91977Cu   // chat display object
#define G_GAMESTATE   0x917BB8u   // game state (+0x2CC = game time for the chat line)

// unit (EEComplexUnit)
#define U_NEXT   0x0C
#define U_ID     0x24
#define U_DB     0x2C
#define U_UCU    0x34
#define U_HP     0x3C
#define U_TRANS  0x130
#define U_X      0x13C
#define U_Y      0x14C
#define U_Z      0x15C
#define U_UCU2   0x37C
#define U_BEHAVIOR 0x208          // EEUnitBehavior* (stance)
#define G_BEHAVIORS 0x8D2044u     // EEUnitBehavior* table[8]
#define DB_HASBEHAV 0x621         // byte: unit type has a behaviour setting
// db (EEUC*, shared per type)
#define DB_CLASS 0x4B4
#define DB_TYPE  0x4B8
// per player and type stats (EEUnitClassUpgrade, 0x164 bytes)
#define UCU_SIZE   0x164
#define UCU_RANGE  0x9C
#define UCU_LOS    0xA4
#define UCU_SPEED  0xA8
#define UCU_RELOAD 0x138  // int, ms
#define UCU_MAXHP  0x144  // int
// player
#define P_UNITS  0x450
#define P_SLOT   0x464
#define P_SELGRP 0x9BC
// projectile -> shooter
#define PROJ_SHOOTER 0x1E0

// DirectInput (DIK codes / mouse offsets)
#define DIK_ESCAPE 0x01
#define DIK_1 0x02
#define DIK_2 0x03
#define DIK_3 0x04
#define DIK_4 0x05
#define DIK_Q 0x10
#define DIK_W 0x11
#define DIK_A 0x1E
#define DIK_S 0x1F
#define DIK_D 0x20
#define DIK_LSHIFT 0x2A

template <class T> static inline T& at(void* p, unsigned off) { return *(T*)((char*)p + off); }
#define PTR(a) ((void*)(uintptr_t)(a))

// ------------------------------------------------------------------ config
struct Weapon { char name[32]; int reloadMs; float dmgMult; float range; float zoom; };
static struct Config {
    int   toggleKey;          // DIK code
    int   filterMessages;
    float sens, eye, forward, pitchMax, fov, nearClip, farClip;
    int   invertY;
    float heroHpMult, heroDamageTaken, heroRegenPct, minRange, minLos;
    int   heroBehavior;
    float aimRadius, moveStep, lookAhead;
    DWORD skyColor, crossColor, hitColor;
    float crossSize;
    int   hud;
    int   nWeapons;
    Weapon w[6];
} C;

static char g_dir[MAX_PATH];
static FILE* g_log;
static void logf(const char* fmt, ...) {
    if (!g_log) return;
    SYSTEMTIME t; GetLocalTime(&t);
    fprintf(g_log, "%02d:%02d:%02d.%03d ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
    va_list a; va_start(a, fmt); vfprintf(g_log, fmt, a); va_end(a);
    fputc('\n', g_log); fflush(g_log);
}

static float inif(const char* ini, const char* sec, const char* key, float def) {
    char b[64], d[64]; sprintf_s(d, "%g", def);
    GetPrivateProfileStringA(sec, key, d, b, sizeof b, ini);
    return (float)atof(b);
}

static DWORD inih(const char* ini, const char* sec, const char* key, DWORD def) {   // accepts 0x.. and decimal
    char b[64]; GetPrivateProfileStringA(sec, key, "", b, sizeof b, ini);
    if (!b[0]) return def;
    return (DWORD)strtoul(b, NULL, 0);
}

// in-game messages: German unless ee_fps.ini says  [Steuerung] Sprache=en
static bool g_en = false;
#define TX(de, en) (g_en ? (en) : (de))

static void load_config() {
    char ini[MAX_PATH]; sprintf_s(ini, "%s\\ee_fps.ini", g_dir);
    { char lang[8]; GetPrivateProfileStringA("Steuerung", "Sprache", "de", lang, sizeof lang, ini);
      g_en = (lang[0] == 'e' || lang[0] == 'E'); }
    C.toggleKey      = (int)inih(ini, "Steuerung", "Umschalttaste", 0x29);   // ^ on a German keyboard
    C.filterMessages = GetPrivateProfileIntA("Steuerung", "FensterNachrichtenFiltern", 0, ini);
    C.sens           = inif(ini, "Steuerung", "Mausempfindlichkeit", 0.0025f);
    C.invertY        = GetPrivateProfileIntA("Steuerung", "MausYInvertieren", 0, ini);
    C.eye            = inif(ini, "Kamera", "Augenhoehe", 0.65f);
    C.forward        = inif(ini, "Kamera", "Vorversatz", 0.35f);
    C.pitchMax       = inif(ini, "Kamera", "MaxNeigungGrad", 60.0f);
    C.fov            = inif(ini, "Kamera", "Sichtfeld", 0.0f);          // 0 = like the game (0.79 rad)
    C.nearClip       = inif(ini, "Kamera", "NahClip", 0.05f);
    C.farClip        = inif(ini, "Kamera", "FernClip", 70.0f);
    C.heroHpMult     = inif(ini, "Held", "LebenFaktor", 10.0f);
    C.heroDamageTaken= inif(ini, "Held", "ErlittenerSchadenFaktor", 0.35f);
    C.heroRegenPct   = inif(ini, "Held", "RegenerationProzentProSekunde", 1.0f);
    C.heroBehavior   = GetPrivateProfileIntA("Held", "Verhalten", 6, ini);
    C.minRange       = inif(ini, "Held", "MinReichweite", 9.0f);
    C.minLos         = inif(ini, "Held", "MinSichtweite", 12.0f);
    C.aimRadius      = inif(ini, "Zielen", "Trefferradius", 0.55f);
    C.moveStep       = inif(ini, "Zielen", "Laufschritt", 2.5f);
    C.lookAhead      = inif(ini, "Kamera", "WeltVorlauf", 6.0f);
    C.skyColor       = inih(ini, "Kamera", "Himmelfarbe", 0x7FA6CC) | 0xFF000000u;
    C.crossColor     = inih(ini, "Fadenkreuz", "Farbe", 0x30FF30) | 0xFF000000u;
    C.hitColor       = inih(ini, "Fadenkreuz", "TrefferFarbe", 0xFF3030) | 0xFF000000u;
    C.crossSize      = inif(ini, "Fadenkreuz", "Groesse", 1.0f);
    C.hud            = GetPrivateProfileIntA("Fadenkreuz", "Anzeige", 1, ini);
    static const Weapon defs[4] = {
        { "Standardwaffe", 0,    2.0f,  9.0f, 1.0f },
        { "AK-47",         250,  1.2f, 10.0f, 1.0f },
        { "AWP",           2600, 12.0f, 16.0f, 4.0f },
        { "Desert Eagle",  700,  3.5f,  9.0f, 1.0f },
    };
    C.nWeapons = 0;
    for (int i = 0; i < 6; i++) {
        char sec[16]; sprintf_s(sec, "Waffe%d", i + 1);
        Weapon w = i < 4 ? defs[i] : Weapon{ "", 0, 0, 0, 1.0f };
        GetPrivateProfileStringA(sec, "Name", w.name, w.name, sizeof w.name, ini);
        if (!w.name[0]) break;
        w.reloadMs = GetPrivateProfileIntA(sec, "NachladezeitMs", w.reloadMs, ini);
        w.dmgMult  = inif(ini, sec, "SchadenFaktor", w.dmgMult);
        w.range    = inif(ini, sec, "Reichweite", w.range);
        w.zoom     = inif(ini, sec, "Zoom", w.zoom);
        if (w.zoom < 1.0f) w.zoom = 1.0f;
        C.w[C.nWeapons++] = w;
    }
}

// ------------------------------------------------------------------ hooking helpers
static void* hook(uintptr_t target, int len, const char* expect, void* detour) {
    BYTE* t = (BYTE*)target;
    if (memcmp(t, expect, len) != 0) { logf("hook %08X: unexpected bytes, skipped", (unsigned)target); return NULL; }
    BYTE* tr = (BYTE*)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(tr, t, len);
    tr[len] = 0xE9; *(DWORD*)(tr + len + 1) = (DWORD)(t + len - (tr + len + 5));
    DWORD old; VirtualProtect(t, len, PAGE_EXECUTE_READWRITE, &old);
    t[0] = 0xE9; *(DWORD*)(t + 1) = (DWORD)((BYTE*)detour - (t + 5));
    for (int i = 5; i < len; i++) t[i] = 0x90;
    VirtualProtect(t, len, old, &old);
    FlushInstructionCache(GetCurrentProcess(), t, len);
    return tr;
}

// ------------------------------------------------------------------ engine / game functions
typedef void  (__thiscall* SetCamera_t)(void* vp, void* trans);
typedef long  (__thiscall* UpdateUI_t)(void* mgr, void* pt);
typedef void  (__thiscall* Refresh_t)(void* dev);
typedef void  (__thiscall* SetPos_t)(void* t, float x, float y, float z);
typedef void  (__thiscall* SetYPR_t)(void* t, float y, float p, float r);
typedef float (__thiscall* GetF_t)(void* o);
typedef void  (__thiscall* SetF_t)(void* o, float v);
typedef void* (__thiscall* Lookup_t)(void* world, unsigned id);
typedef void  (__thiscall* Exec_t)(void* msg);
typedef void  (__thiscall* Damage_t)(void* target, void* src, int dmg, int a3, int a4);
typedef void* (__cdecl* OpNew_t)(unsigned);
typedef void* (__thiscall* UcuCtor_t)(void* obj, void* db);
typedef unsigned (__thiscall* GrpCount_t)(void* grp);
typedef void* (__thiscall* GrpItem_t)(void* grp, unsigned i);

static SetCamera_t o_SetCamera;
static UpdateUI_t  o_UpdateUI;
static Refresh_t   o_KbdRefresh, o_MouseRefresh;
static Damage_t    o_Damage;
static SetPos_t    e_SetPos;
static SetYPR_t    e_SetYPR;
static GetF_t      e_GetYaw, e_GetFov, e_GetFront, e_GetRear;
static SetF_t      e_SetFov, e_SetFront, e_SetRear;

static Lookup_t  g_lookup  = (Lookup_t)F_LOOKUP;
static Exec_t    x_select  = (Exec_t)F_EXEC_SELECT;
static Exec_t    x_unsel   = (Exec_t)F_EXEC_UNSEL;
static Exec_t    x_attack  = (Exec_t)F_EXEC_ATTACK;
static Exec_t    x_pathto  = (Exec_t)F_EXEC_PATHTO;
static Exec_t    x_halt    = (Exec_t)F_EXEC_HALT;
static OpNew_t   g_new     = (OpNew_t)F_OPNEW;
static UcuCtor_t g_ucuCtor = (UcuCtor_t)F_UCU_CTOR;

// ------------------------------------------------------------------ input state (all on the game thread)
static void* g_mouseDev;
static void* g_kbdDev;
typedef HRESULT(__stdcall* GetState_t)(void* self, DWORD cb, void* data);
typedef HRESULT(__stdcall* GetData_t)(void* self, DWORD cb, void* data, DWORD* inout, DWORD flags);
static GetState_t o_GetState;
static GetData_t  o_GetData;

static volatile LONG in_dx, in_dy, in_wheel;
static bool in_key[256], in_keyHit[256];
static bool in_btn[4], in_btnHit[4];
static volatile bool in_toggle;

// ------------------------------------------------------------------ mode state
static struct State {
    bool   active;
    void*  unit;
    unsigned id;
    void*  player;
    int    slot;
    void*  origUcu;
    void*  heroUcu;
    int    origMaxHp, heroMaxHp;
    float  origRange, origLos;
    int    origReload;
    int    weapon, lastWeapon;
    float  yaw, pitch;
    float  camPos[3], fwd[3], right[3];
    bool   camValid;
    void*  viewport;
    float  saveFov, saveFront, saveRear;
    bool   clipSaved;
    BYTE   rtsCam[0x40];
    void*  rtsPtr;
    bool   rtsSaved;
    void*  target;
    DWORD  lastMove, lastAim, lastRegen, enterTick;
    bool   moving;
    float  moveTo[2];
    DWORD  lastAttack, lastHit;
    bool   naturalRange;
    float  regenAcc;
    void*  origBehavior;
    int    shots, hits;
    DWORD  fireUntil, clickTick, hitFlash;
    bool   zoomed;
} S;

static bool g_ok;        // code bytes matched, hooks installed
struct D3DVP7 { DWORD x, y, w, h; float mn, mx; };
static D3DVP7 g_vp3d;      // 3D viewport (screen pixels), taken from the device while the sky is drawn
static bool g_vpValid;
static bool g_restoreCursor;   // put the game's cursor back to the middle after leaving

// ------------------------------------------------------------------ game helpers
static void* player_by_index(unsigned i) { return i < 9 ? *(void**)PTR(G_PLAYERS + i * 4) : NULL; }
static bool network_game() {
    void* comm = *(void**)PTR(G_COMM);
    return comm && at<BYTE>(comm, 0x2E) != 0;
}
static void* lookup(unsigned id) { return g_lookup(PTR(G_WORLD), id); }

struct Msg { BYTE b[0x30]; };
static void msg_init(Msg& m, int slot) { memset(&m, 0, sizeof m); m.b[0x0A] = (BYTE)slot; }

static void cmd_select_only(void* unit) {
    Msg m; msg_init(m, S.slot); x_unsel(&m);
    msg_init(m, S.slot); at<unsigned>(&m, 0x10) = at<unsigned>(unit, U_ID); x_select(&m);
}
static void cmd_attack(void* target) {
    Msg m; msg_init(m, S.slot); at<unsigned>(&m, 0x10) = at<unsigned>(target, U_ID); m.b[0x14] = 0; x_attack(&m);
    S.shots++;
}
static void cmd_path(float x, float y, float angle) {
    Msg m; msg_init(m, S.slot);
    at<float>(&m, 0x10) = angle; at<float>(&m, 0x14) = x; at<float>(&m, 0x18) = y;
    m.b[0x1C] = 1; m.b[0x1D] = 1; m.b[0x1E] = 0; m.b[0x1F] = 0;
    x_pathto(&m);
}
static void cmd_halt() { Msg m; msg_init(m, S.slot); x_halt(&m); }

static void* sel_group(void* player) { return at<void*>(player, P_SELGRP); }
static unsigned sel_count(void* g) { void** vt = *(void***)g; return ((GrpCount_t)vt[6])(g); }
static void* sel_item(void* g, unsigned i) { void** vt = *(void***)g; return ((GrpItem_t)vt[5])(g, i); }

// in-game text line (the game's own chat window): EEChatDisplay::Add(color, name, text, time, 0)
typedef void (__thiscall* ChatAdd_t)(void* disp, void* a1, void* a2, void* text, unsigned a4, unsigned a5);
typedef void* (__thiscall* WStrCtor_t)(void* w, const char* s);
typedef void (__thiscall* WStrDtor_t)(void* w);
static WStrCtor_t e_WStrCtor;
static WStrDtor_t e_WStrDtor;
static char g_msg[200];
static bool g_msgPending;
static void say(const char* fmt, ...) {
    va_list a; va_start(a, fmt); vsprintf_s(g_msg, fmt, a); va_end(a);
    g_msgPending = true;
    logf("MSG %s", g_msg);
}
static void flush_msg() {
    if (!g_msgPending || !e_WStrCtor) return;
    g_msgPending = false;
    void* disp = *(void**)PTR(G_CHATDISP);
    void* pl = player_by_index(*(unsigned*)PTR(G_LOCAL));
    void* gs = *(void**)PTR(G_GAMESTATE);
    if (!disp || !pl || !gs) return;
    __try {
        BYTE w[0x40] = { 0 };
        char line[220]; sprintf_s(line, "[Ego] %s", g_msg);
        e_WStrCtor(w, line);
        ((ChatAdd_t)F_CHAT_ADD)(disp, (char*)pl + 0x438, (char*)pl + 0x24, w, at<unsigned>(gs, 0x2CC), 0);
        e_WStrDtor(w);
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("chat display failed"); }
}

// ------------------------------------------------------------------ hero stats
static void apply_weapon(int w) {
    if (!S.heroUcu || w < 0 || w >= C.nWeapons) return;
    const Weapon& W = C.w[w];
    float rng = W.range; if (rng < C.minRange) rng = C.minRange; if (rng < S.origRange) rng = S.origRange;
    if (S.naturalRange) rng = S.origRange;     // bows, slings, ...: projectiles cannot fly further
    at<float>(S.heroUcu, UCU_RANGE) = rng;
    float los = rng + 2.0f; if (los < C.minLos) los = C.minLos; if (los < S.origLos) los = S.origLos;
    at<float>(S.heroUcu, UCU_LOS) = los;
    at<int>(S.heroUcu, UCU_RELOAD) = W.reloadMs > 0 ? W.reloadMs : S.origReload;
    if (w != S.weapon) S.lastWeapon = S.weapon;
    S.weapon = w;
    S.zoomed = false;
    say(TX("Waffe %d: %s  (Nachladen %d ms, Schaden x%.1f, Reichweite %.0f)",
           "Weapon %d: %s  (reload %d ms, damage x%.1f, range %.0f)"), w + 1, W.name,
        at<int>(S.heroUcu, UCU_RELOAD), W.dmgMult, rng);
}

static bool make_hero(void* unit) {
    void* orig = at<void*>(unit, U_UCU);
    void* db = at<void*>(unit, U_DB);
    if (!orig || !db) return false;
    void* c = g_new(UCU_SIZE);
    if (!c) return false;
    g_ucuCtor(c, db);
    memcpy((char*)c + 0x84, (char*)orig + 0x84, 0x154 - 0x84);   // numbers incl. the player's upgrades
    at<int>(c, 0x154) = 1;     // reference counts (units using this object); only the hero uses the copy
    at<int>(c, 0x158) = 1;
    S.origUcu = orig; S.heroUcu = c;
    S.origMaxHp = at<int>(orig, UCU_MAXHP);
    S.origRange = at<float>(orig, UCU_RANGE);
    S.origLos = at<float>(orig, UCU_LOS);
    S.origReload = at<int>(orig, UCU_RELOAD);
    S.heroMaxHp = (int)(S.origMaxHp * C.heroHpMult);
    at<int>(c, UCU_MAXHP) = S.heroMaxHp;
    at<void*>(unit, U_UCU) = c;
    at<void*>(unit, U_UCU2) = c;
    // behaviour: do not run after enemies on its own (the player steers); EEMSetUnitBehavior does the same write
    S.origBehavior = at<void*>(unit, U_BEHAVIOR);
    void** table = *(void***)PTR(G_BEHAVIORS);
    if (table && C.heroBehavior >= 0 && C.heroBehavior < 8 && at<BYTE>(db, DB_HASBEHAV) && table[C.heroBehavior])
        at<void*>(unit, U_BEHAVIOR) = table[C.heroBehavior];
    int hp = at<int>(unit, U_HP);
    at<int>(unit, U_HP) = (int)(hp * C.heroHpMult);
    S.weapon = -1; S.lastWeapon = 0;
    apply_weapon(0);
    return true;
}

static void unmake_hero(bool alive) {
    if (!S.unit || !S.origUcu) return;
    if (alive) {
        __try {
            if (at<void*>(S.unit, U_UCU) == S.heroUcu) {
                at<void*>(S.unit, U_UCU) = S.origUcu;
                at<void*>(S.unit, U_UCU2) = S.origUcu;
                if (S.origBehavior) at<void*>(S.unit, U_BEHAVIOR) = S.origBehavior;
                int hp = at<int>(S.unit, U_HP);
                int nh = (int)ceilf(hp / C.heroHpMult);
                if (nh > S.origMaxHp) nh = S.origMaxHp;
                if (hp > 0 && nh < 1) nh = 1;
                at<int>(S.unit, U_HP) = nh;
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    // the clone is left allocated on purpose: a dying unit may still read it
    S.origUcu = NULL; S.heroUcu = NULL;
}

// ------------------------------------------------------------------ enter / leave
static void leave(const char* why, bool alive) {
    if (!S.active) return;
    logf("leave: %s (shots %d, hits %d)", why, S.shots, S.hits);
    unmake_hero(alive);
    if (alive && S.moving) { __try { cmd_halt(); } __except (EXCEPTION_EXECUTE_HANDLER) {} }
    if (alive) {   // put the RTS camera onto the unit
        __try {
            at<float>(PTR(G_CAMOBJ), 0x40) = at<float>(S.unit, U_X);
            at<float>(PTR(G_CAMOBJ), 0x44) = at<float>(S.unit, U_Y);
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    if (S.viewport && S.clipSaved) {
        e_SetFront(S.viewport, S.saveFront); e_SetRear(S.viewport, S.saveRear); e_SetFov(S.viewport, S.saveFov);
    }
    if (S.rtsSaved && S.rtsPtr) memcpy(S.rtsPtr, S.rtsCam, 0x40);
    __try { *(volatile BYTE*)PTR(G_CAMCLEAN) = 0; } __except (EXCEPTION_EXECUTE_HANDLER) {}   // redraw the RTS view
    g_restoreCursor = true;
    S.active = false; S.unit = NULL; S.target = NULL; S.camValid = false; S.clipSaved = false; S.rtsSaved = false;
    memset(in_key, 0, sizeof in_key); memset(in_btn, 0, sizeof in_btn);
    say(TX("Ego-Modus beendet (%s)", "First-person mode ended (%s)"), why);
}

static void try_enter() {
    if (network_game()) { say(TX("Ego-Modus: nur im Einzelspieler", "First-person mode: single player only")); return; }
    unsigned li = *(unsigned*)PTR(G_LOCAL);
    void* pl = player_by_index(li);
    if (!pl) return;
    void* g = sel_group(pl);
    if (!g || sel_count(g) != 1) { say(TX("Ego-Modus: genau EINE eigene Fernkampf-Einheit auswaehlen",
                                          "First-person mode: select exactly ONE of your own ranged units")); return; }
    void* u = sel_item(g, 0);
    if (!u) return;
    unsigned id = at<unsigned>(u, U_ID);
    if ((id >> 24) != li || lookup(id) != u || at<int>(u, U_HP) <= 0) { say(TX("Ego-Modus: keine eigene Einheit", "First-person mode: not one of your units")); return; }
    void* db = at<void*>(u, U_DB);
    int cls = at<int>(db, DB_CLASS);
    void* ucu = at<void*>(u, U_UCU);
    float rng = ucu ? at<float>(ucu, UCU_RANGE) : 0;
    if ((cls != 5 && cls != 6) || rng < 1.5f) { say(TX("Ego-Modus: nur Fernkampf-Einheiten (Schuetzen, Bogenschuetzen, ...)",
                                                        "First-person mode: ranged units only (riflemen, archers, ...)")); return; }

    memset(&S, 0, sizeof S);
    S.unit = u; S.id = id; S.player = pl; S.slot = at<BYTE>(pl, P_SLOT);
    if (!make_hero(u)) { say(TX("Ego-Modus: Werte konnten nicht gesetzt werden", "First-person mode: could not set the unit values")); return; }
    S.yaw = e_GetYaw((char*)u + U_TRANS);
    S.pitch = -5.0f * 3.14159265f / 180.0f;
    S.active = true;
    S.enterTick = S.lastRegen = GetTickCount();
    in_dx = in_dy = in_wheel = 0;
    memset(in_key, 0, sizeof in_key); memset(in_keyHit, 0, sizeof in_keyHit);
    memset(in_btn, 0, sizeof in_btn); memset(in_btnHit, 0, sizeof in_btnHit);
    logf("enter: unit %p id %08X type %d hp %d -> %d range %.1f", u, id, at<int>(db, DB_TYPE),
         S.origMaxHp, S.heroMaxHp, at<float>(S.heroUcu, UCU_RANGE));
}

// ------------------------------------------------------------------ aiming
static void* pick_target(float maxRange) {
    if (!S.camValid) return NULL;
    unsigned li = *(unsigned*)PTR(G_LOCAL);
    float ux = at<float>(S.unit, U_X), uy = at<float>(S.unit, U_Y);
    void* best = NULL; float bestT = 1e9f;
    for (unsigned i = 0; i < 9; i++) {
        if (i == li) continue;
        void* p = player_by_index(i);
        if (!p) continue;
        for (void* o = at<void*>(p, P_UNITS); o; o = at<void*>(o, U_NEXT)) {
            int hp = at<int>(o, U_HP);
            if (hp <= 0) continue;
            void* db = at<void*>(o, U_DB);
            if (!db) continue;
            int cls = at<int>(db, DB_CLASS);
            float rad = C.aimRadius, h = 0.5f;
            if (cls == 0 || cls == 1) continue;                 // ambient objects, resources (trees, rocks, ...)
            if (cls == 2) { rad = 1.2f; h = 0.8f; }            // buildings
            if (i == 0 && cls == 2) continue;
            float px = at<float>(o, U_X), py = at<float>(o, U_Y), pz = at<float>(o, U_Z) + h;
            float hd = hypotf(px - ux, py - uy);
            if (hd > maxRange + rad) continue;
            float vx = px - S.camPos[0], vy = py - S.camPos[1], vz = pz - S.camPos[2];
            float t = vx * S.fwd[0] + vy * S.fwd[1] + vz * S.fwd[2];
            if (t < 0.3f) continue;
            float cx = vx - t * S.fwd[0], cy = vy - t * S.fwd[1], cz = vz - t * S.fwd[2];
            float d = sqrtf(cx * cx + cy * cy + cz * cz);
            if (d > rad + 0.015f * t) continue;
            if (o == S.target) return o;          // keep the current target while it is under the crosshair
            if (t < bestT) { bestT = t; best = o; }
        }
    }
    return best;
}

// ------------------------------------------------------------------ per frame (game thread, from UIManager::UpdateUI)
static void frame_active() {
    DWORD now = GetTickCount();
    void* u = S.unit;
    if (lookup(S.id) != u || at<int>(u, U_HP) <= 0) { leave(TX("Einheit gefallen", "unit killed"), false); return; }
    void* g = sel_group(S.player);
    if (!g || sel_count(g) != 1 || sel_item(g, 0) != u) { leave(TX("Einheit abgewaehlt", "unit deselected"), true); return; }

    // ---- keys
    if (in_keyHit[DIK_ESCAPE] || in_toggle) { in_toggle = false; memset(in_keyHit, 0, sizeof in_keyHit); leave(TX("Taste", "key"), true); return; }
    for (int k = 0; k < C.nWeapons && k < 6; k++) if (in_keyHit[DIK_1 + k]) apply_weapon(k);
    if (in_keyHit[DIK_Q]) apply_weapon(S.lastWeapon);
    LONG wh = InterlockedExchange(&in_wheel, 0);
    if (wh) apply_weapon((S.weapon + (wh < 0 ? 1 : C.nWeapons - 1)) % C.nWeapons);
    memset(in_keyHit, 0, sizeof in_keyHit);

    // ---- look
    LONG dx = InterlockedExchange(&in_dx, 0), dy = InterlockedExchange(&in_dy, 0);
    float sens = C.sens / (S.zoomed ? C.w[S.weapon].zoom : 1.0f);
    S.yaw -= dx * sens;
    if (S.yaw > 3.14159265f) S.yaw -= 6.2831853f;
    if (S.yaw < -3.14159265f) S.yaw += 6.2831853f;
    S.pitch += (C.invertY ? dy : -dy) * sens;
    float pm = C.pitchMax * 3.14159265f / 180.0f;
    if (S.pitch > pm) S.pitch = pm;
    if (S.pitch < -pm) S.pitch = -pm;

    // ---- shoot (has priority over walking: the unit stops to fire)
    // A click fires one shot: the unit has to turn and wait for its reload, so the attack order stays alive
    // until a hit was registered or the shot window ran out. Holding the button keeps firing (automatic).
    bool held = in_btn[0], click = in_btnHit[0];
    in_btnHit[0] = false;
    if (in_btnHit[1]) {   // right mouse: scope for weapons with a zoom factor
        in_btnHit[1] = false;
        S.zoomed = !S.zoomed && C.w[S.weapon].zoom > 1.0f;
    }
    if ((held || click) && (click || now - S.lastAim > 60)) {
        S.lastAim = now;
        float rng = at<float>(S.heroUcu, UCU_RANGE);
        void* t = pick_target(rng);
        if (click) S.clickTick = now;
        if (t) {
            int reload = at<int>(S.heroUcu, UCU_RELOAD);
            DWORD window = (DWORD)(reload < 400 ? 400 : reload) + 900;
            if (t != S.target || now > S.fireUntil) { cmd_attack(t); S.lastAttack = now; }
            S.target = t; S.moving = false;
            if (click || S.fireUntil < now + 200) S.fireUntil = now + window;
        }
    }
    if (S.target && !held) {
        bool shotDone = S.clickTick && (int)(S.lastHit - S.clickTick) >= 0;
        if (shotDone || (int)(now - S.fireUntil) > 0) { S.target = NULL; S.clickTick = 0; cmd_halt(); }
    }
    if (S.target && (lookup(at<unsigned>(S.target, U_ID)) != S.target || at<int>(S.target, U_HP) <= 0)) S.target = NULL;
    // weapons with a flying projectile (bows, slings, javelins) do not fire beyond their natural range:
    // if nothing hit for a while, fall back to the unit's own range
    if (S.target && !S.naturalRange && S.origRange < C.minRange) {
        DWORD wait = (DWORD)(at<int>(S.heroUcu, UCU_RELOAD) * 3.0f); if (wait < 6000) wait = 6000;
        float td = hypotf(at<float>(S.target, U_X) - at<float>(u, U_X), at<float>(S.target, U_Y) - at<float>(u, U_Y));
        if (td > S.origRange + 0.5f && now - S.lastAttack > wait && (int)(S.lastHit - S.lastAttack) < 0) {
            S.naturalRange = true;
            apply_weapon(S.weapon);
            say(TX("Diese Waffe traegt nur %.0f Felder weit - Reichweite angepasst",
                   "This weapon only reaches %.0f tiles - range adjusted"), S.origRange);
            cmd_attack(S.target); S.lastAttack = now;
        }
    }

    // ---- walk (re-issue the path only when the direction changes or the goal is nearly reached)
    if (!S.target && now - S.lastMove > 120 && S.camValid) {
        S.lastMove = now;
        float fx = S.fwd[0], fy = S.fwd[1], fl = hypotf(fx, fy);
        float rx = S.right[0], ry = S.right[1], rl = hypotf(rx, ry);
        if (fl > 1e-3f) { fx /= fl; fy /= fl; }
        if (rl > 1e-3f) { rx /= rl; ry /= rl; }
        float mx = 0, my = 0;
        if (in_key[DIK_W]) { mx += fx; my += fy; }
        if (in_key[DIK_S]) { mx -= fx; my -= fy; }
        if (in_key[DIK_D]) { mx += rx; my += ry; }
        if (in_key[DIK_A]) { mx -= rx; my -= ry; }
        float ml = hypotf(mx, my);
        if (ml > 1e-3f) {
            float step = C.moveStep * (in_key[DIK_LSHIFT] ? 0.5f : 1.0f);
            float ux = at<float>(u, U_X), uy = at<float>(u, U_Y);
            float x = ux + mx / ml * step, y = uy + my / ml * step;
            bool reissue = !S.moving;
            if (!reissue) {
                float gx = S.moveTo[0] - ux, gy = S.moveTo[1] - uy, gl = hypotf(gx, gy);
                if (gl < step * 0.6f) reissue = true;                                  // nearly there
                else if ((gx * mx + gy * my) / (gl * ml) < 0.97f) reissue = true;       // direction changed (>14 deg)
            }
            if (reissue) {
                cmd_path(x, y, atan2f(my, mx));
                S.moveTo[0] = x; S.moveTo[1] = y;
                S.moving = true;
            }
        } else if (S.moving) { cmd_halt(); S.moving = false; }
    }

    // ---- the game draws terrain, trees and units only around the point the (hidden) RTS camera looks at:
    // keep that point a little in front of the unit, so the world in view is complete
    __try {
        float fx = S.fwd[0], fy = S.fwd[1], fl = hypotf(fx, fy);
        if (fl > 1e-3f) { fx /= fl; fy /= fl; } else { fx = 0; fy = 0; }
        float lx = at<float>(u, U_X) + fx * C.lookAhead, ly = at<float>(u, U_Y) + fy * C.lookAhead;
        at<float>(PTR(G_CAMOBJ), 0x40) = lx; at<float>(PTR(G_CAMOBJ), 0x44) = ly;
        at<float>(PTR(G_CAMOBJ), 0x78) = lx; at<float>(PTR(G_CAMOBJ), 0x7C) = ly;
        // the renderer only calls SetCamera and re-transforms the terrain when the camera counts as changed;
        // otherwise the ground stays in the old (bird's eye) projection behind the first-person objects
        *(volatile BYTE*)PTR(G_CAMCLEAN) = 0;
    } __except (EXCEPTION_EXECUTE_HANDLER) {}

    // ---- hero regeneration
    if (now - S.lastRegen >= 250) {
        S.regenAcc += S.heroMaxHp * C.heroRegenPct / 100.0f * (now - S.lastRegen) / 1000.0f;
        S.lastRegen = now;
        int add = (int)S.regenAcc;
        if (add > 0) {
            S.regenAcc -= add;
            int hp = at<int>(u, U_HP) + add;
            at<int>(u, U_HP) = hp > S.heroMaxHp ? S.heroMaxHp : hp;
        }
    }

    // ---- keep the game's cursor (= crosshair) in the middle of the screen, keep the Windows cursor inside
    HWND fg = GetForegroundWindow();
    DWORD pid = 0; GetWindowThreadProcessId(fg, &pid);
    if (pid == GetCurrentProcessId()) {
        RECT r; GetClientRect(fg, &r);
        POINT c = { (r.right - r.left) / 2, (r.bottom - r.top) / 2 };
        ClientToScreen(fg, &c);
        SetCursorPos(c.x, c.y);
    }
}

static void restore_game_cursor(void* mgr) {
    g_restoreCursor = false;
    __try {
        void** b = at<void**>(mgr, 0x30); void** e = at<void**>(mgr, 0x34);
        if (!b || e <= b) return;
        float* pos = &at<float>(e[-1], 0xE4);
        float cx = g_vpValid ? g_vp3d.x + g_vp3d.w / 2.0f : GetSystemMetrics(SM_CXSCREEN) / 2.0f;
        float cy = g_vpValid ? g_vp3d.y + g_vp3d.h / 2.0f : GetSystemMetrics(SM_CYSCREEN) / 2.0f;
        if (pos[0] < 0 || pos[1] < 0) { pos[0] = cx; pos[1] = cy; }
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

static void center_game_cursor(void* mgr) {
    // UIManager +0x30/+0x34 = vector<UIForm*>, top form +0xE4 = cursor position (floats, screen pixels)
    __try {
        void** b = at<void**>(mgr, 0x30); void** e = at<void**>(mgr, 0x34);
        if (!b || e <= b) return;
        void* f = e[-1];
        HWND fg = GetForegroundWindow();
        RECT r; if (!GetClientRect(fg, &r)) return;
        // the game renders at its own resolution; use the form size if known (+0xE0 holds flags, size unknown) ->
        // take the resolution from the viewport ratio of the window client area
        // the crosshair is drawn by this DLL; park the game's arrow cursor outside the screen
        float* pos = &at<float>(f, 0xE4);
        pos[0] = -200.0f; pos[1] = -200.0f;
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

static void frame(void* mgr) {
    if (!g_ok) return;
    __try {
        if (!S.active) {
            if (g_restoreCursor) restore_game_cursor(mgr);
            if (in_toggle) { in_toggle = false; try_enter(); }
            memset(in_keyHit, 0, sizeof in_keyHit);
        } else {
            frame_active();
            if (S.active) center_game_cursor(mgr);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        logf("exception in frame: %08X", GetExceptionCode());
        S.active = false; S.unit = NULL;
    }
    flush_msg();
}

// ------------------------------------------------------------------ hooks
static void init_exe();
static long __fastcall hk_UpdateUI(void* mgr, void*, void* pt) {
    init_exe();
    frame(mgr);
    return o_UpdateUI(mgr, pt);
}

static BYTE g_camT[0x100];
static void __fastcall hk_SetCamera(void* vp, void*, void* t) {
    if (S.active && S.unit) {
        __try {
            S.viewport = vp;
            memcpy(g_camT, t, 0x40);
            void* T = (char*)S.unit + U_TRANS;
            float x = at<float>(T, 0x0C), y = at<float>(T, 0x1C), z = at<float>(T, 0x2C);
            e_SetYPR(g_camT, S.yaw, S.pitch, 0);
            float* m = (float*)g_camT;               // row major, translation in column 3
            // a little in front of the eyes, otherwise the unit's own head and weapon fill the screen
            float hx = -sinf(S.yaw), hy = cosf(S.yaw);
            x += hx * C.forward; y += hy * C.forward;
            e_SetPos(g_camT, x, y, z + C.eye);
            S.right[0] = m[0]; S.right[1] = m[4]; S.right[2] = m[8];
            S.fwd[0] = m[1];   S.fwd[1] = m[5];   S.fwd[2] = m[9];
            S.camPos[0] = x; S.camPos[1] = y; S.camPos[2] = z + C.eye;
            // the caller keeps using the transform it passed (terrain), so overwrite it in place
            if (!S.rtsSaved) { memcpy(S.rtsCam, t, 0x40); S.rtsPtr = t; S.rtsSaved = true; }
            memcpy(t, g_camT, 0x40);
            S.camValid = true;
            if (!S.clipSaved) {
                S.saveFront = e_GetFront(vp); S.saveRear = e_GetRear(vp); S.saveFov = e_GetFov(vp);
                S.clipSaved = true;
            }
            e_SetFront(vp, C.nearClip); e_SetRear(vp, C.farClip);
            float fov = C.fov > 0 ? C.fov : S.saveFov;
            if (S.zoomed && S.weapon >= 0) fov /= C.w[S.weapon].zoom;
            e_SetFov(vp, fov);
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    o_SetCamera(vp, t);
}

// ------------------------------------------------------------------ drawing (DX7Rasterizer of DX7HRDisplay.dll / DX7HRTnLDisplay.dll)
// The game never clears the colour buffer (in the RTS view the terrain covers everything), so in first person the
// old picture stayed visible where no terrain is drawn. Before the sky the 3D area is cleared; at the end of the
// frame the crosshair and a small HUD are drawn as filled rectangles (IDirect3DDevice7::Clear with rectangles).
struct DRECT { LONG x1, y1, x2, y2; };
typedef HRESULT(__stdcall* DevClear_t)(void* dev, DWORD n, const DRECT* r, DWORD flags, DWORD color, float z, DWORD st);
typedef HRESULT(__stdcall* DevGetVp_t)(void* dev, D3DVP7* vp);
typedef long (__thiscall* Begin_t)(void* r, void* surf, unsigned k);
typedef long (__thiscall* End_t)(void* r, unsigned k);
typedef long (__thiscall* Sky_t)(void* r, void* model, unsigned k, float f, bool b);
static Begin_t o_Begin[2];
static End_t   o_End[2];
static Sky_t   o_Sky[2];
static bool    g_skyDone;

static void* rast_device(void* r, unsigned k) {
    void** arr = at<void**>(r, 0x6C);
    if (!arr || k > 7) return NULL;
    void* so = arr[k];
    return so ? at<void*>(so, 0x1C) : NULL;
}
static void dev_fill(void* dev, const DRECT* r, int n, DWORD color) {
    if (n > 0) ((DevClear_t)(*(void***)dev)[10])(dev, n, r, 1 /*D3DCLEAR_TARGET*/, color, 1.0f, 0);
}
static void draw_hud(void* dev) {
    if (!g_vpValid) return;
    float s = g_vp3d.h / 1000.0f * C.crossSize; if (s < 0.6f) s = 0.6f;
    LONG cx = g_vp3d.x + g_vp3d.w / 2, cy = g_vp3d.y + g_vp3d.h / 2;
    LONG gap = (LONG)(5 * s + 1), len = (LONG)(11 * s + 2), th = (LONG)(1.6f * s + 0.5f); if (th < 2) th = 2;
    LONG h0 = th / 2, h1 = th - h0;
    DRECT r[8];
    r[0] = { cx - gap - len, cy - h0, cx - gap, cy + h1 };
    r[1] = { cx + gap, cy - h0, cx + gap + len, cy + h1 };
    r[2] = { cx - h0, cy - gap - len, cx + h1, cy - gap };
    r[3] = { cx - h0, cy + gap, cx + h1, cy + gap + len };
    r[4] = { cx - 1, cy - 1, cx + 1, cy + 1 };             // centre dot
    DRECT o[5];
    for (int i = 0; i < 5; i++) o[i] = { r[i].x1 - 1, r[i].y1 - 1, r[i].x2 + 1, r[i].y2 + 1 };
    DWORD now = GetTickCount();
    bool hit = S.hitFlash && now - S.hitFlash < 180;
    dev_fill(dev, o, 5, 0xFF000000);
    dev_fill(dev, r, 5, hit ? C.hitColor : C.crossColor);
    if (S.zoomed) {   // scope: dark frame around a square view
        LONG half = (LONG)(g_vp3d.h * 0.45f);
        DRECT b[4] = {
            { (LONG)g_vp3d.x, (LONG)g_vp3d.y, cx - half, (LONG)(g_vp3d.y + g_vp3d.h) },
            { cx + half, (LONG)g_vp3d.y, (LONG)(g_vp3d.x + g_vp3d.w), (LONG)(g_vp3d.y + g_vp3d.h) },
            { cx - half, (LONG)g_vp3d.y, cx + half, cy - half },
            { cx - half, cy + half, cx + half, (LONG)(g_vp3d.y + g_vp3d.h) } };
        dev_fill(dev, b, 4, 0xFF101010);
        DRECT l[2] = { { cx - half, cy, cx - gap, cy + 1 }, { cx + gap, cy, cx + half, cy + 1 } };
        dev_fill(dev, l, 2, 0xFF000000);
    }
    if (!C.hud || !S.unit || !S.heroMaxHp) return;
    // health bar (bottom left of the 3D area) and weapon slots
    LONG bx = g_vp3d.x + (LONG)(20 * s), by = g_vp3d.y + g_vp3d.h - (LONG)(40 * s);
    LONG bw = (LONG)(260 * s), bh = (LONG)(14 * s);
    int hp = 0; __try { hp = at<int>(S.unit, U_HP); } __except (EXCEPTION_EXECUTE_HANDLER) {}
    float f = (float)hp / S.heroMaxHp; if (f < 0) f = 0; if (f > 1) f = 1;
    DRECT bg = { bx - 2, by - 2, bx + bw + 2, by + bh + 2 };
    dev_fill(dev, &bg, 1, 0xFF000000);
    DRECT fg = { bx, by, bx + (LONG)(bw * f), by + bh };
    DWORD col = f > 0.5f ? 0xFF30D030 : f > 0.25f ? 0xFFE0C020 : 0xFFE03020;
    dev_fill(dev, &fg, 1, col);
    LONG sw = (LONG)(26 * s), sx = bx + bw + (LONG)(24 * s);
    for (int i = 0; i < C.nWeapons; i++) {
        DRECT q = { sx + i * (sw + 6), by - (LONG)(6 * s), sx + i * (sw + 6) + sw, by + bh };
        dev_fill(dev, &q, 1, 0xFF000000);
        DRECT in = { q.x1 + 2, q.y1 + 2, q.x2 - 2, q.y2 - 2 };
        dev_fill(dev, &in, 1, i == S.weapon ? C.crossColor : 0xFF505050);
    }
}

// The sky is drawn last (depth 1), so the 3D area is cleared right after BeginScene, using the 3D viewport
// remembered from the previous frame's sky call.
static void begin_post(void* r, unsigned k) {
    g_skyDone = false;
    if (!S.active || !g_vpValid) return;
    __try {
        void* dev = rast_device(r, k);
        if (!dev) return;
        DRECT a = { (LONG)g_vp3d.x, (LONG)g_vp3d.y, (LONG)(g_vp3d.x + g_vp3d.w), (LONG)(g_vp3d.y + g_vp3d.h) };
        D3DVP7 cur, full = { 0, 0, 0, 0, 0.0f, 1.0f };
        DevGetVp_t gv = (DevGetVp_t)(*(void***)dev)[15];
        typedef HRESULT(__stdcall* DevSetVp_t)(void*, D3DVP7*);
        DevSetVp_t sv = (DevSetVp_t)(*(void***)dev)[13];
        if (FAILED(gv(dev, &cur))) return;
        full.w = a.x2; full.h = a.y2;
        sv(dev, &full);   // Clear rectangles are clipped to the current viewport
        ((DevClear_t)(*(void***)dev)[10])(dev, 1, &a, 1 /*TARGET*/, C.skyColor, 1.0f, 0);
        sv(dev, &cur);
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}
static long __fastcall hk_Begin0(void* r, void*, void* surf, unsigned k) { long h = o_Begin[0](r, surf, k); begin_post(r, k); return h; }
static long __fastcall hk_Begin1(void* r, void*, void* surf, unsigned k) { long h = o_Begin[1](r, surf, k); begin_post(r, k); return h; }
static void sky_pre(void* r, unsigned k) {
    if (!S.active || g_skyDone) return;
    g_skyDone = true;
    __try {
        void* dev = rast_device(r, k);
        if (!dev) return;
        D3DVP7 vp;
        if (SUCCEEDED(((DevGetVp_t)(*(void***)dev)[15])(dev, &vp)) && vp.w > 100 && vp.h > 100) { g_vp3d = vp; g_vpValid = true; }
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}
static long __fastcall hk_Sky0(void* r, void*, void* m, unsigned k, float f, bool b) { sky_pre(r, k); return o_Sky[0](r, m, k, f, b); }
static long __fastcall hk_Sky1(void* r, void*, void* m, unsigned k, float f, bool b) { sky_pre(r, k); return o_Sky[1](r, m, k, f, b); }
static void end_pre(void* r, unsigned k) {
    if (!S.active || !g_skyDone) return;     // only frames that drew the 3D world
    __try { void* dev = rast_device(r, k); if (dev) draw_hud(dev); } __except (EXCEPTION_EXECUTE_HANDLER) {}
}
static long __fastcall hk_End0(void* r, void*, unsigned k) { end_pre(r, k); return o_End[0](r, k); }
static long __fastcall hk_End1(void* r, void*, unsigned k) { end_pre(r, k); return o_End[1](r, k); }

static void hook_display(int i, const char* dll) {
    HMODULE m = GetModuleHandleA(dll);
    if (!m) return;
    void* b = (void*)GetProcAddress(m, "?BeginScene@DX7Rasterizer@@UAEJPAVGESurface@@K@Z");
    void* e = (void*)GetProcAddress(m, "?EndScene@DX7Rasterizer@@UAEJK@Z");
    void* k = (void*)GetProcAddress(m, "?DrawSky@DX7Rasterizer@@UAEJPAVGEModel@@KM_N@Z");
    if (!b || !e || !k) { logf("%s: rasterizer exports missing", dll); return; }
    o_Begin[i] = (Begin_t)hook((uintptr_t)b, 7, "\x53\x56\x57\x8B\x7C\x24\x14", i ? (void*)hk_Begin1 : (void*)hk_Begin0);
    o_End[i]   = (End_t)hook((uintptr_t)e, 5, "\x8B\x44\x24\x04\x53", i ? (void*)hk_End1 : (void*)hk_End0);
    o_Sky[i]   = (Sky_t)hook((uintptr_t)k, 8, "\xFF\x74\x24\x10\xD9\x44\x24\x10", i ? (void*)hk_Sky1 : (void*)hk_Sky0);
    logf("%s: draw hooks %d%d%d", dll, o_Begin[i] != 0, o_End[i] != 0, o_Sky[i] != 0);
}

static void __fastcall hk_Damage(void* target, void*, void* src, int dmg, int a3, int a4) {
    if (S.active && S.unit && dmg > 0) {
        __try {
            if (target == S.unit) {
                int nd = (int)ceilf(dmg * C.heroDamageTaken);
                dmg = nd < 1 ? 1 : nd;
            } else if (src && (src == S.unit || at<void*>(src, PROJ_SHOOTER) == S.unit)) {
                int d0 = dmg;
                if (S.weapon >= 0 && S.weapon < C.nWeapons) dmg = (int)ceilf(dmg * C.w[S.weapon].dmgMult);
                logf("hit: weapon %d damage %d -> %d, target hp %d", S.weapon + 1, d0, dmg, at<int>(target, U_HP));
                S.hits++;
                S.lastHit = S.hitFlash = GetTickCount();
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    o_Damage(target, src, dmg, a3, a4);
}

// DirectInput device methods. Keyboard and mouse usually share one vtable; keep the originals per vtable anyway.
static struct { void** vt; GetState_t st; GetData_t dt; } g_vts[4];
static int g_nvts;
static GetState_t orig_state(void* self) {
    void** vt = *(void***)self;
    for (int i = 0; i < g_nvts; i++) if (g_vts[i].vt == vt) return g_vts[i].st;
    return o_GetState;
}
static GetData_t orig_data(void* self) {
    void** vt = *(void***)self;
    for (int i = 0; i < g_nvts; i++) if (g_vts[i].vt == vt) return g_vts[i].dt;
    return o_GetData;
}
static HRESULT __stdcall hk_GetState(void* self, DWORD cb, void* data) {
    HRESULT hr = orig_state(self)(self, cb, data);
    if (SUCCEEDED(hr) && data && S.active) {
        if (self == g_mouseDev && cb >= 12) {
            LONG* s = (LONG*)data;
            InterlockedExchangeAdd(&in_dx, s[0]); InterlockedExchangeAdd(&in_dy, s[1]);
            if (s[2]) InterlockedExchangeAdd(&in_wheel, s[2]);
            memset(data, 0, cb);
        } else if (self == g_kbdDev) {
            memset(data, 0, cb);
        }
    }
    return hr;
}

struct DIOD { DWORD ofs, data, time, seq; };
static HRESULT __stdcall hk_GetData(void* self, DWORD cb, void* data, DWORD* inout, DWORD flags) {
    HRESULT hr = orig_data(self)(self, cb, data, inout, flags);
    if (FAILED(hr) || !data || !inout || cb != sizeof(DIOD) || (flags & 1 /*DIGDD_PEEK*/)) return hr;
    DIOD* d = (DIOD*)data;
    DWORD n = *inout, w = 0;
    bool mouse = self == g_mouseDev;
    if (!mouse && !g_kbdDev && self != g_mouseDev) g_kbdDev = self;
    for (DWORD i = 0; i < n; i++) {
        bool keep = true, down = (d[i].data & 0x80) != 0;
        DWORD ofs = d[i].ofs;
        if (mouse) {
            if (S.active) {
                if (ofs >= 12 && ofs < 16) { in_btn[ofs - 12] = down; if (down) { in_btnHit[ofs - 12] = true; keep = false; } }
                else if (ofs == 8) { keep = false; }      // wheel comes via GetDeviceState
                else if (ofs == 0 || ofs == 4) keep = false;
            }
        } else if (self == g_kbdDev && ofs < 256) {
            if ((int)ofs == C.toggleKey && down) { in_toggle = true; keep = false; }
            else if (S.active) { in_key[ofs] = down; if (down) { in_keyHit[ofs] = true; keep = false; } }
        }
        if (keep) d[w++] = d[i];
    }
    *inout = w;
    return hr;
}

static void hook_device(void* dev) {
    if (!dev) return;
    void** vt = *(void***)dev;
    if (vt[9] == (void*)hk_GetState || g_nvts >= 4) return;
    DWORD old;
    if (!VirtualProtect(&vt[9], 8, PAGE_EXECUTE_READWRITE, &old)) return;
    g_vts[g_nvts].vt = vt; g_vts[g_nvts].st = (GetState_t)vt[9]; g_vts[g_nvts].dt = (GetData_t)vt[10];
    if (!o_GetState) { o_GetState = g_vts[g_nvts].st; o_GetData = g_vts[g_nvts].dt; }
    g_nvts++;
    vt[9] = (void*)hk_GetState; vt[10] = (void*)hk_GetData;
    VirtualProtect(&vt[9], 8, old, &old);
    logf("dinput device %p hooked (vtable %p)", dev, vt);
}

// Window messages: in first-person mode keyboard and mouse messages must not reach the game's UI either
// (hotkeys, clicks). The game's own message loop calls DispatchMessageA through its import table.
typedef LRESULT(WINAPI* Dispatch_t)(const MSG*);
static Dispatch_t o_Dispatch;
static LRESULT WINAPI hk_Dispatch(const MSG* m) {
    if (S.active && m) {
        UINT k = m->message;
        bool keyDown = k == WM_KEYDOWN || k == WM_CHAR || k == WM_DEADCHAR || k == WM_SYSCHAR
                    || (k == WM_SYSKEYDOWN && m->wParam != VK_F4 && m->wParam != VK_TAB);
        bool mouse = (k >= WM_MOUSEMOVE && k <= WM_MOUSELAST && k != WM_LBUTTONUP && k != WM_RBUTTONUP && k != WM_MBUTTONUP);
        if (keyDown || mouse) return 0;
    }
    return o_Dispatch(m);
}
// replace every import slot of `mod` that currently points at `real` (compares addresses, needs no name tables)
static void hook_iat(HMODULE mod, void* real, void* detour, void** orig) {
    if (!mod || !real) return;
    __try {
        BYTE* b = (BYTE*)mod;
        IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(b + ((IMAGE_DOS_HEADER*)b)->e_lfanew);
        IMAGE_DATA_DIRECTORY dd = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
        if (!dd.VirtualAddress) return;
        for (IMAGE_IMPORT_DESCRIPTOR* d = (IMAGE_IMPORT_DESCRIPTOR*)(b + dd.VirtualAddress); d->Name && d->FirstThunk; d++) {
            for (DWORD* slot = (DWORD*)(b + d->FirstThunk); *slot; slot++) {
                if (*slot != (DWORD)real) continue;
                DWORD old;
                if (!VirtualProtect(slot, 4, PAGE_EXECUTE_READWRITE, &old)) continue;   // the page may also hold code
                *orig = real;
                *slot = (DWORD)detour;
                VirtualProtect(slot, 4, old, &old);
                logf("import slot %p of module %p patched", slot, mod);
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("import patch failed in module %p", mod); }
}

// dgVoodoo draws the mouse pointer itself from GetCursorPos. In first-person mode it is pushed out of the
// picture (the crosshair replaces it); everything else keeps the real position.
typedef BOOL(WINAPI* GetCursorPos_t)(POINT*);
static GetCursorPos_t o_GetCursorPos;
static BOOL WINAPI hk_GetCursorPos(POINT* p) {
    BOOL r = o_GetCursorPos(p);
    if (r && p && S.active) { p->x = -4000; p->y = -4000; }
    return r;
}

// some modules (dgVoodoo) fill their own function pointer table instead of a normal import table:
// replace every pointer to `real` in the module (packed modules keep it in an executable section)
static int hook_ptrs(HMODULE mod, void* real, void* detour, void** orig) {
    int n = 0;
    if (!mod || !real) return 0;
    __try {
        BYTE* b = (BYTE*)mod;
        IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(b + ((IMAGE_DOS_HEADER*)b)->e_lfanew);
        IMAGE_SECTION_HEADER* sh = IMAGE_FIRST_SECTION(nt);
        for (int i = 0; i < nt->FileHeader.NumberOfSections; i++, sh++) {
            if (!(sh->Characteristics & IMAGE_SCN_MEM_READ)) continue;
            DWORD* p = (DWORD*)(b + sh->VirtualAddress);
            DWORD cnt = sh->Misc.VirtualSize / 4;
            for (DWORD k = 0; k < cnt; k++) {
                if (p[k] != (DWORD)real) continue;
                DWORD old;
                if (!VirtualProtect(&p[k], 4, PAGE_EXECUTE_READWRITE, &old)) continue;
                *orig = real; p[k] = (DWORD)detour; n++;
                VirtualProtect(&p[k], 4, old, &old);
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("pointer patch failed in module %p", mod); }
    logf("module %p: %d pointer(s) redirected", mod, n);
    return n;
}

static void __fastcall hk_MouseRefresh(void* m, void*) {
    void* dev = at<void*>(m, 0x44);
    if (dev != g_mouseDev) { g_mouseDev = dev; hook_device(dev); }
    o_MouseRefresh(m);
}
static void __fastcall hk_KbdRefresh(void* k, void*) {
    void* dev = at<void*>(k, 0x18);
    if (dev != g_kbdDev) { g_kbdDev = dev; hook_device(dev); }
    o_KbdRefresh(k);
}

// ------------------------------------------------------------------ debug interface (Frida tests in the sandbox)
extern "C" __declspec(dllexport) void fps_sim(int dx, int dy, int key, int keyDown, int btn, int btnDown) {
    InterlockedExchangeAdd(&in_dx, dx); InterlockedExchangeAdd(&in_dy, dy);
    if (key == -1) in_toggle = true;
    else if (key > 0 && key < 256) { in_key[key] = keyDown != 0; if (keyDown) in_keyHit[key] = true; }
    if (btn >= 0 && btn < 4) { in_btn[btn] = btnDown != 0; if (btnDown) in_btnHit[btn] = true; }
}
extern "C" __declspec(dllexport) const char* fps_state() {
    static char b[512];
    void* u = S.unit;
    sprintf_s(b, "{\"ok\":%d,\"active\":%d,\"unit\":\"%p\",\"hp\":%d,\"heroMax\":%d,\"weapon\":%d,\"yaw\":%.3f,\"pitch\":%.3f,"
                 "\"pos\":[%.2f,%.2f],\"fwd\":[%.2f,%.2f,%.2f],\"right\":[%.2f,%.2f,%.2f],\"target\":\"%p\",\"shots\":%d,\"hits\":%d,"
                 "\"mouse\":\"%p\",\"kbd\":\"%p\",\"natural\":%d,\"msg\":\"%s\"}",
              g_ok, S.active, u, u ? at<int>(u, U_HP) : 0, S.heroMaxHp, S.weapon, S.yaw, S.pitch,
              u ? at<float>(u, U_X) : 0.f, u ? at<float>(u, U_Y) : 0.f, S.fwd[0], S.fwd[1], S.fwd[2],
              S.right[0], S.right[1], S.right[2], S.target, S.shots, S.hits, g_mouseDev, g_kbdDev, S.naturalRange, g_msg);
    return b;
}

// ------------------------------------------------------------------ init
static FARPROC eng(HMODULE m, const char* n) {
    FARPROC p = GetProcAddress(m, n);
    if (!p) logf("engine export missing: %s", n);
    return p;
}

static DWORD WINAPI init(void*) {
    load_config();
    HMODULE m = GetModuleHandleA("Low-Level Engine.dll");
    if (!m || (uintptr_t)GetModuleHandleA(NULL) != 0x400000) { logf("not Empire Earth"); return 0; }
    e_SetPos   = (SetPos_t)eng(m, "?SetPosition@GETransformation@@QAEXMMM@Z");
    e_SetYPR   = (SetYPR_t)eng(m, "?SetOrientationYPR@GETransformation@@QAEXMMM@Z");
    e_GetYaw   = (GetF_t)eng(m, "?GetYaw@GETransformation@@QBEMXZ");
    e_GetFov   = (GetF_t)eng(m, "?GetFieldOfView@GEViewport@@QBEMXZ");
    e_GetFront = (GetF_t)eng(m, "?GetFrontClippingDistance@GEViewport@@QBEMXZ");
    e_GetRear  = (GetF_t)eng(m, "?GetRearClippingDistance@GEViewport@@QBEMXZ");
    e_SetFov   = (SetF_t)eng(m, "?SetFieldOfView@GEViewport@@QAEXM@Z");
    e_SetFront = (SetF_t)eng(m, "?SetFrontClippingDistance@GEViewport@@QAEXM@Z");
    e_SetRear  = (SetF_t)eng(m, "?SetRearClippingDistance@GEViewport@@QAEXM@Z");
    e_WStrCtor = (WStrCtor_t)eng(m, "??0UWideString@@QAE@PBD@Z");
    e_WStrDtor = (WStrDtor_t)eng(m, "??1UWideString@@UAE@XZ");
    uintptr_t setCam  = (uintptr_t)eng(m, "?SetCamera@GEViewport@@QAEXABVGETransformation@@@Z");
    uintptr_t updUI   = (uintptr_t)eng(m, "?UpdateUI@UIManager@@UAEJABVGE2DPoint@@@Z");
    uintptr_t mRef    = (uintptr_t)eng(m, "?Refresh@ISMouse@@UAEXXZ");
    uintptr_t kRef    = (uintptr_t)eng(m, "?Refresh@ISKeyboard@@UAEXXZ");
    if (!e_SetPos || !e_SetYPR || !e_GetYaw || !e_SetFront || !setCam || !updUI || !mRef || !kRef) return 0;
    // engine hooks now; the exe's own functions are checked and hooked on the first UI frame
    // (the NeoEE executable is still being prepared while the DLL loads)
    o_UpdateUI     = (UpdateUI_t)hook(updUI, 6, "\x55\x8B\xEC\x83\xEC\x14", (void*)hk_UpdateUI);
    o_SetCamera    = (SetCamera_t)hook(setCam, 8, "\x56\x8B\xF1\x57\xFF\x74\x24\x0C", (void*)hk_SetCamera);
    o_MouseRefresh = (Refresh_t)hook(mRef, 8, "\x55\x8B\xEC\xB8\x1C\x10\x00\x00", (void*)hk_MouseRefresh);
    o_KbdRefresh   = (Refresh_t)hook(kRef, 8, "\x55\x8B\xEC\xB8\x08\x10\x00\x00", (void*)hk_KbdRefresh);
    logf("ee_fps loaded, engine hooks %d%d%d%d, toggle key 0x%02X, %d weapons",
         o_UpdateUI != 0, o_SetCamera != 0, o_MouseRefresh != 0, o_KbdRefresh != 0, C.toggleKey, C.nWeapons);
    return 0;
}

static void init_exe() {   // first UI frame
    static bool done;
    if (done) return;
    done = true;
    static const char dmgSig[] = "\x55\x8B\xEC\x83\xEC\x28";
    static const char haltSig[] = "\x55\x8B\xEC\x51\x8A\x41\x0A";
    static const char ctorSig[] = "\x56\x8B\xF1\x57\x8D\x4E\x04";
    static const char chatSig[] = "\x55\x8B\xEC\x53\x56\x57\x6A\x3C";
    int bad = (memcmp(PTR(F_EXEC_HALT), haltSig, 7) != 0) | (memcmp(PTR(F_UCU_CTOR), ctorSig, 7) != 0) << 1
            | (memcmp(PTR(F_DAMAGE), dmgSig, 6) != 0) << 2 | (memcmp(PTR(F_CHAT_ADD), chatSig, 8) != 0) << 3;
    if (bad) {
        const BYTE* d = (const BYTE*)PTR(F_DAMAGE);
        logf("exe build does not match (mask %d, damage starts %02X %02X %02X %02X %02X %02X), FPS mode disabled",
             bad, d[0], d[1], d[2], d[3], d[4], d[5]);
        return;
    }
    o_Damage = (Damage_t)hook(F_DAMAGE, 6, dmgSig, (void*)hk_Damage);
    {
        void* real = (void*)GetProcAddress(GetModuleHandleA("user32.dll"), "GetCursorPos");
        hook_ptrs(GetModuleHandleA("DDraw.dll"), real, (void*)hk_GetCursorPos, (void**)&o_GetCursorPos);
        if (!o_GetCursorPos) logf("GetCursorPos of the display wrapper not found - the arrow stays visible");
    }
    hook_display(0, "DX7HRDisplay.dll");
    hook_display(1, "DX7HRTnLDisplay.dll");
    if (C.filterMessages) {
        void* realDispatch = (void*)GetProcAddress(GetModuleHandleA("user32.dll"), "DispatchMessageA");
        hook_iat(GetModuleHandleA(NULL), realDispatch, (void*)hk_Dispatch, (void**)&o_Dispatch);
        hook_iat(GetModuleHandleA("Low-Level Engine.dll"), realDispatch, (void*)hk_Dispatch, (void**)&o_Dispatch);
    }
    g_ok = o_Damage && o_SetCamera && o_UpdateUI && o_MouseRefresh && o_KbdRefresh;
    logf("ee_fps ready=%d", g_ok);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        // The engine loads every DLL of the game folder once as a possible plugin and unloads it again.
        // Only become active inside the cheat exe (its patch starts with the marker EECHEAT1 in the PE header page),
        // so the normal "Empire Earth.exe" (also used online) never runs any of this code.
        __try {
            if (memcmp(PTR(0x400460), "EECHEAT1", 8) != 0) return TRUE;
        } __except (EXCEPTION_EXECUTE_HANDLER) { return TRUE; }
        // stay loaded for the rest of the process: the hooks point into this module
        HMODULE self;
        GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, (LPCSTR)&DllMain, &self);
        GetModuleFileNameA(h, g_dir, MAX_PATH);
        char* s = strrchr(g_dir, '\\'); if (s) *s = 0;
        char lp[MAX_PATH]; sprintf_s(lp, "%s\\ee_fps.log", g_dir);
        g_log = _fsopen(lp, "w", _SH_DENYNO);
        init(NULL);
    }
    return TRUE;
}
