#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>

namespace {

constexpr std::int32_t kScePadErrorFatal =
    static_cast<std::int32_t>(UINT32_C(0x809200FF));
constexpr std::uint64_t kInvalidControllerHandle = 0;
constexpr std::int64_t kExpectedSteamApiSize = 242976;
constexpr int kPadSlots = 4;
constexpr int kMaximumSteamControllers = 16;
constexpr int kMaximumOutputRequests = 16;
constexpr ULONGLONG kStateFreshnessMilliseconds = 250;
constexpr DWORD kActiveWorkerIntervalMilliseconds = 16;
constexpr DWORD kIdleWorkerIntervalMilliseconds = 100;
constexpr ULONGLONG kSteamRetryMilliseconds = 1000;
constexpr float kTiltMaximumAngleRadians = 0.7853981633974483F; // 45 degrees.

constexpr std::uint32_t kScePadButtonOptions = UINT32_C(0x00000008);
constexpr std::uint32_t kScePadButtonDpadUp = UINT32_C(0x00000010);
constexpr std::uint32_t kScePadButtonDpadRight = UINT32_C(0x00000020);
constexpr std::uint32_t kScePadButtonDpadDown = UINT32_C(0x00000040);
constexpr std::uint32_t kScePadButtonDpadLeft = UINT32_C(0x00000080);
constexpr std::uint32_t kScePadButtonL2 = UINT32_C(0x00000100);
constexpr std::uint32_t kScePadButtonR2 = UINT32_C(0x00000200);
constexpr std::uint32_t kScePadButtonL1 = UINT32_C(0x00000400);
constexpr std::uint32_t kScePadButtonR1 = UINT32_C(0x00000800);
constexpr std::uint32_t kScePadButtonTriangle = UINT32_C(0x00001000);
constexpr std::uint32_t kScePadButtonCircle = UINT32_C(0x00002000);
constexpr std::uint32_t kScePadButtonCross = UINT32_C(0x00004000);
constexpr std::uint32_t kScePadButtonSquare = UINT32_C(0x00008000);
constexpr std::uint32_t kScePadButtonTouchpad = UINT32_C(0x00100000);

struct ScePadData {
    std::uint32_t buttons;
    std::uint8_t left_stick_x;
    std::uint8_t left_stick_y;
    std::uint8_t right_stick_x;
    std::uint8_t right_stick_y;
    std::uint8_t left_trigger;
    std::uint8_t right_trigger;
    std::uint8_t alignment_0[2];
    float orientation[4];
    float acceleration[3];
    float angular_velocity[3];
    std::uint8_t touch_data[24];
    std::uint8_t connected;
    std::uint8_t alignment_1[3];
    std::uint64_t timestamp;
    std::uint8_t extension_data[16];
    std::uint8_t connected_count;
    std::uint8_t reserved[15];
};

struct ScePadVibrationParam {
    std::uint8_t large_motor;
    std::uint8_t small_motor;
};

struct ScePadLightBarParam {
    std::uint8_t red;
    std::uint8_t green;
    std::uint8_t blue;
};

struct ControllerDigitalActionData {
    bool state;
    bool active;
};

struct ControllerAnalogActionData {
    std::int32_t mode;
    float x;
    float y;
    bool active;
    std::uint8_t padding[3];
};


static_assert(sizeof(ScePadData) == 0x78);
static_assert(offsetof(ScePadData, orientation) == 0x0C);
static_assert(offsetof(ScePadData, acceleration) == 0x1C);
static_assert(offsetof(ScePadData, angular_velocity) == 0x28);
static_assert(offsetof(ScePadData, connected) == 0x4C);
static_assert(offsetof(ScePadData, timestamp) == 0x50);
static_assert(offsetof(ScePadData, connected_count) == 0x68);
static_assert(sizeof(ScePadVibrationParam) == 2);
static_assert(sizeof(ScePadLightBarParam) == 3);
static_assert(sizeof(ControllerDigitalActionData) == 2);
static_assert(sizeof(ControllerAnalogActionData) == 16);
static_assert(offsetof(ControllerAnalogActionData, active) == 12);

using ScePadOpenFunction = std::int32_t (*)(std::int32_t user_id, std::int32_t type,
                                            std::int32_t index, const void* parameters);
using ScePadCloseFunction = std::int32_t (*)(std::int32_t handle);
using ScePadReadStateFunction = std::int32_t (*)(std::int32_t handle, ScePadData* data);
using ScePadSetVibrationFunction =
    std::int32_t (*)(std::int32_t handle, const ScePadVibrationParam* vibration);
using ScePadSetLightBarFunction =
    std::int32_t (*)(std::int32_t handle, const ScePadLightBarParam* light_bar);

using SteamCreateInterfaceFunction = void* (*)(const char* version);
using SteamGetHandleFunction = std::int32_t (*)();
using SteamGetControllerInterfaceFunction = void* (*)(void* client, std::int32_t user,
                                                      std::int32_t pipe,
                                                      const char* version);
using SteamControllerInitFunction = bool (*)(void* controller);
using SteamControllerRunFrameFunction = void (*)(void* controller);
using SteamGetConnectedControllersFunction = int (*)(void* controller,
                                                     std::uint64_t* handles);
using SteamGetGamepadIndexForControllerFunction = int (*)(void* controller,
                                                          std::uint64_t handle);
using SteamGetActionSetHandleFunction = std::uint64_t (*)(void* controller,
                                                          const char* name);
using SteamActivateActionSetFunction = void (*)(void* controller, std::uint64_t handle,
                                                std::uint64_t action_set);
using SteamGetDigitalActionHandleFunction = std::uint64_t (*)(void* controller,
                                                              const char* name);
using SteamGetDigitalActionDataFunction = ControllerDigitalActionData (*)(
    void* controller, std::uint64_t handle, std::uint64_t action);
using SteamGetAnalogActionHandleFunction = std::uint64_t (*)(void* controller,
                                                             const char* name);
using SteamGetAnalogActionDataFunction = ControllerAnalogActionData (*)(
    void* controller, std::uint64_t handle, std::uint64_t action);
using SteamTriggerVibrationFunction = void (*)(void* controller, std::uint64_t handle,
                                               std::uint16_t left_speed,
                                               std::uint16_t right_speed);
using SteamSetLedColorFunction = void (*)(void* controller, std::uint64_t handle,
                                          std::uint8_t red, std::uint8_t green,
                                          std::uint8_t blue, std::uint32_t flags);

struct OriginalApi {
    HMODULE module;
    ScePadOpenFunction open;
    ScePadCloseFunction close;
    ScePadReadStateFunction read_state;
    ScePadSetVibrationFunction set_vibration;
    ScePadSetLightBarFunction set_light_bar;
};

struct ActionHandles {
    std::uint64_t action_set;
    std::uint64_t left_stick;
    std::uint64_t right_stick;
    std::uint64_t tilt;
    std::uint64_t dpad_up;
    std::uint64_t dpad_right;
    std::uint64_t dpad_down;
    std::uint64_t dpad_left;
    std::uint64_t square;
    std::uint64_t cross;
    std::uint64_t circle;
    std::uint64_t triangle;
    std::uint64_t l1;
    std::uint64_t r1;
    std::uint64_t l2;
    std::uint64_t r2;
    std::uint64_t options;
    std::uint64_t touchpad_click;
};

struct SteamApi {
    HMODULE module;
    void* controller;
    SteamControllerRunFrameFunction run_frame;
    SteamGetConnectedControllersFunction get_connected_controllers;
    SteamGetGamepadIndexForControllerFunction get_gamepad_index;
    SteamGetActionSetHandleFunction get_action_set_handle;
    SteamActivateActionSetFunction activate_action_set;
    SteamGetDigitalActionHandleFunction get_digital_action_handle;
    SteamGetDigitalActionDataFunction get_digital_action_data;
    SteamGetAnalogActionHandleFunction get_analog_action_handle;
    SteamGetAnalogActionDataFunction get_analog_action_data;
    SteamTriggerVibrationFunction trigger_vibration;
    SteamSetLedColorFunction set_led_color;
    ActionHandles actions;
    ULONGLONG retry_after;
    ULONGLONG action_retry_after;
};

struct NamedActionSnapshot {
    float left_stick_x;
    float left_stick_y;
    float right_stick_x;
    float right_stick_y;
    float acceleration[3];
    std::uint32_t buttons;
    bool tilt_valid;
    bool active;
};

struct RuntimeSlot {
    std::int32_t native_handle;
    int preferred_index;
    std::uint64_t steam_handle;
    ScePadData published_state;
    ULONGLONG published_tick;
    std::uint64_t generation;
    std::uint8_t connected_count;
    std::uint8_t last_large_motor;
    std::uint8_t last_small_motor;
    ScePadLightBarParam last_light_bar;
    bool open;
    bool owner_active;
    bool state_valid;
    bool vibration_known;
    bool light_bar_known;
};

struct WorkerAssignment {
    int slot_index;
    std::int32_t native_handle;
    std::uint64_t steam_handle;
    std::uint64_t generation;
};

struct WorkerSample {
    WorkerAssignment assignment;
    NamedActionSnapshot actions;
    ULONGLONG sample_tick;
};

struct OutputTarget {
    int slot_index;
    std::int32_t native_handle;
    std::uint64_t steam_handle;
    std::uint64_t generation;
};

struct OutputRequest {
    OutputTarget target;
    std::uint16_t left_speed;
    std::uint16_t right_speed;
    ScePadLightBarParam light_bar;
    bool occupied;
    bool owner_bound;
    bool vibration_dirty;
    bool light_bar_dirty;
};

HMODULE g_proxy_module = nullptr;
HMODULE g_worker_module_pin = nullptr;
SRWLOCK g_original_lock = SRWLOCK_INIT;
SRWLOCK g_state_lock = SRWLOCK_INIT;
SRWLOCK g_output_lock = SRWLOCK_INIT;
SRWLOCK g_debug_lock = SRWLOCK_INIT;
INIT_ONCE g_worker_once = INIT_ONCE_STATIC_INIT;
HANDLE g_worker_wake_event = nullptr;
OriginalApi g_original{};
SteamApi g_steam{}; // Accessed only by the worker thread.
RuntimeSlot g_slots[kPadSlots]{};
OutputRequest g_output_requests[kMaximumOutputRequests]{};

bool environment_flag_enabled(const char* name) {
    char value[8]{};
    const DWORD length = GetEnvironmentVariableA(name, value, sizeof(value));
    return length > 0 && length < sizeof(value) && value[0] == '1';
}

bool debug_enabled() {
    return environment_flag_enabled("FLOWER_INPUT_DEBUG") ||
           environment_flag_enabled("FLOWER_GYRO_DEBUG");
}

bool make_sibling_path(const wchar_t* filename, wchar_t* output, DWORD capacity) {
    if (g_proxy_module == nullptr || filename == nullptr || output == nullptr ||
        capacity == 0) {
        return false;
    }
    const DWORD length = GetModuleFileNameW(g_proxy_module, output, capacity);
    if (length == 0 || length >= capacity) {
        return false;
    }
    wchar_t* separator = std::wcsrchr(output, L'\\');
    if (separator == nullptr) {
        return false;
    }
    ++separator;
    const std::size_t remaining =
        capacity - static_cast<std::size_t>(separator - output);
    return wcscpy_s(separator, remaining, filename) == 0;
}

bool file_has_expected_size(const wchar_t* path, std::int64_t expected_size) {
    WIN32_FILE_ATTRIBUTE_DATA attributes{};
    if (!GetFileAttributesExW(path, GetFileExInfoStandard, &attributes) ||
        (attributes.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
        return false;
    }
    const std::uint64_t size =
        (static_cast<std::uint64_t>(attributes.nFileSizeHigh) << 32U) |
        static_cast<std::uint64_t>(attributes.nFileSizeLow);
    return size == static_cast<std::uint64_t>(expected_size);
}

bool module_path_matches(HMODULE module, const wchar_t* expected_path) {
    wchar_t actual[MAX_PATH]{};
    const DWORD length = GetModuleFileNameW(module, actual, MAX_PATH);
    return length > 0 && length < MAX_PATH && _wcsicmp(actual, expected_path) == 0;
}

void debug_log(const char* message) {
    if (!debug_enabled() || message == nullptr) {
        return;
    }

    wchar_t path[MAX_PATH]{};
    if (!make_sibling_path(L"flower_input_bridge.log", path, MAX_PATH)) {
        return;
    }

    AcquireSRWLockExclusive(&g_debug_lock);
    HANDLE file =
        CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                    OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file != INVALID_HANDLE_VALUE) {
        DWORD written = 0;
        (void)WriteFile(file, message, static_cast<DWORD>(std::strlen(message)),
                        &written, nullptr);
        CloseHandle(file);
    }
    ReleaseSRWLockExclusive(&g_debug_lock);
}

template <typename Function> Function load_export(HMODULE module, const char* name) {
    return reinterpret_cast<Function>(GetProcAddress(module, name));
}

bool load_original_api() {
    AcquireSRWLockShared(&g_original_lock);
    const bool already_loaded = g_original.module != nullptr;
    ReleaseSRWLockShared(&g_original_lock);
    if (already_loaded) {
        return true;
    }

    AcquireSRWLockExclusive(&g_original_lock);
    if (g_original.module != nullptr) {
        ReleaseSRWLockExclusive(&g_original_lock);
        return true;
    }

    wchar_t path[MAX_PATH]{};
    if (!make_sibling_path(L"libScePad_original.dll", path, MAX_PATH)) {
        ReleaseSRWLockExclusive(&g_original_lock);
        return false;
    }

    OriginalApi candidate{};
    candidate.module = LoadLibraryW(path);
    if (candidate.module == nullptr || !module_path_matches(candidate.module, path)) {
        if (candidate.module != nullptr) {
            FreeLibrary(candidate.module);
        }
        ReleaseSRWLockExclusive(&g_original_lock);
        debug_log("FlowerInput: failed to load libScePad_original.dll\r\n");
        return false;
    }

    candidate.open = load_export<ScePadOpenFunction>(candidate.module, "scePadOpen");
    candidate.close = load_export<ScePadCloseFunction>(candidate.module, "scePadClose");
    candidate.read_state =
        load_export<ScePadReadStateFunction>(candidate.module, "scePadReadState");
    candidate.set_vibration =
        load_export<ScePadSetVibrationFunction>(candidate.module, "scePadSetVibration");
    candidate.set_light_bar =
        load_export<ScePadSetLightBarFunction>(candidate.module, "scePadSetLightBar");

    const bool complete = candidate.open != nullptr && candidate.close != nullptr &&
                          candidate.read_state != nullptr &&
                          candidate.set_vibration != nullptr &&
                          candidate.set_light_bar != nullptr;
    if (complete) {
        g_original = candidate;
    } else {
        FreeLibrary(candidate.module);
    }
    ReleaseSRWLockExclusive(&g_original_lock);

    if (!complete) {
        debug_log("FlowerInput: original ScePad exports are incomplete\r\n");
    }
    return complete;
}

bool acquire_steam_controller_worker() {
    if (g_steam.controller != nullptr) {
        return true;
    }

    const ULONGLONG now = GetTickCount64();
    if (now < g_steam.retry_after) {
        return false;
    }
    g_steam.retry_after = now + kSteamRetryMilliseconds;

    wchar_t path[MAX_PATH]{};
    if (!make_sibling_path(L"steam_api64.dll", path, MAX_PATH) ||
        !file_has_expected_size(path, kExpectedSteamApiSize)) {
        debug_log("FlowerInput: unsupported sibling steam_api64.dll\r\n");
        return false;
    }

    HMODULE module = LoadLibraryW(path);
    if (module == nullptr || !module_path_matches(module, path)) {
        if (module != nullptr) {
            FreeLibrary(module);
        }
        debug_log("FlowerInput: failed to load Flower's steam_api64.dll\r\n");
        return false;
    }

    const auto create_interface = load_export<SteamCreateInterfaceFunction>(
        module, "SteamInternal_CreateInterface");
    const auto get_user =
        load_export<SteamGetHandleFunction>(module, "SteamAPI_GetHSteamUser");
    const auto get_pipe =
        load_export<SteamGetHandleFunction>(module, "SteamAPI_GetHSteamPipe");
    const auto get_controller_interface =
        load_export<SteamGetControllerInterfaceFunction>(
            module, "SteamAPI_ISteamClient_GetISteamController");
    const auto initialize = load_export<SteamControllerInitFunction>(
        module, "SteamAPI_ISteamController_Init");
    const auto run_frame = load_export<SteamControllerRunFrameFunction>(
        module, "SteamAPI_ISteamController_RunFrame");
    const auto get_connected = load_export<SteamGetConnectedControllersFunction>(
        module, "SteamAPI_ISteamController_GetConnectedControllers");
    const auto get_gamepad_index =
        load_export<SteamGetGamepadIndexForControllerFunction>(
            module, "SteamAPI_ISteamController_GetGamepadIndexForController");
    const auto get_action_set = load_export<SteamGetActionSetHandleFunction>(
        module, "SteamAPI_ISteamController_GetActionSetHandle");
    const auto activate_action_set = load_export<SteamActivateActionSetFunction>(
        module, "SteamAPI_ISteamController_ActivateActionSet");
    const auto get_digital_handle = load_export<SteamGetDigitalActionHandleFunction>(
        module, "SteamAPI_ISteamController_GetDigitalActionHandle");
    const auto get_digital_data = load_export<SteamGetDigitalActionDataFunction>(
        module, "SteamAPI_ISteamController_GetDigitalActionData");
    const auto get_analog_handle = load_export<SteamGetAnalogActionHandleFunction>(
        module, "SteamAPI_ISteamController_GetAnalogActionHandle");
    const auto get_analog_data = load_export<SteamGetAnalogActionDataFunction>(
        module, "SteamAPI_ISteamController_GetAnalogActionData");

    const bool required_exports =
        create_interface != nullptr && get_user != nullptr && get_pipe != nullptr &&
        get_controller_interface != nullptr && initialize != nullptr &&
        run_frame != nullptr && get_connected != nullptr &&
        get_gamepad_index != nullptr && get_action_set != nullptr &&
        activate_action_set != nullptr && get_digital_handle != nullptr &&
        get_digital_data != nullptr && get_analog_handle != nullptr &&
        get_analog_data != nullptr;
    if (!required_exports) {
        FreeLibrary(module);
        debug_log("FlowerInput: required SteamController005 exports are missing\r\n");
        return false;
    }

    void* client = create_interface("SteamClient017");
    const std::int32_t user = get_user();
    const std::int32_t pipe = get_pipe();
    if (client == nullptr || user == 0 || pipe == 0) {
        FreeLibrary(module);
        debug_log("FlowerInput: Steam API is not initialized yet\r\n");
        return false;
    }

    void* controller =
        get_controller_interface(client, user, pipe, "SteamController005");
    if (controller == nullptr || !initialize(controller)) {
        FreeLibrary(module);
        debug_log("FlowerInput: SteamController005 initialization failed\r\n");
        return false;
    }

    g_steam.module = module;
    g_steam.controller = controller;
    g_steam.run_frame = run_frame;
    g_steam.get_connected_controllers = get_connected;
    g_steam.get_gamepad_index = get_gamepad_index;
    g_steam.get_action_set_handle = get_action_set;
    g_steam.activate_action_set = activate_action_set;
    g_steam.get_digital_action_handle = get_digital_handle;
    g_steam.get_digital_action_data = get_digital_data;
    g_steam.get_analog_action_handle = get_analog_handle;
    g_steam.get_analog_action_data = get_analog_data;
    g_steam.trigger_vibration = load_export<SteamTriggerVibrationFunction>(
        module, "SteamAPI_ISteamController_TriggerVibration");
    g_steam.set_led_color = load_export<SteamSetLedColorFunction>(
        module, "SteamAPI_ISteamController_SetLEDColor");
    debug_log("FlowerInput: acquired SteamController005 on worker\r\n");
    return true;
}

bool action_handles_complete(const ActionHandles& actions) {
    return actions.action_set != 0 && actions.left_stick != 0 &&
           actions.right_stick != 0 && actions.tilt != 0 && actions.dpad_up != 0 &&
           actions.dpad_right != 0 && actions.dpad_down != 0 &&
           actions.dpad_left != 0 && actions.square != 0 && actions.cross != 0 &&
           actions.circle != 0 && actions.triangle != 0 && actions.l1 != 0 &&
           actions.r1 != 0 && actions.l2 != 0 && actions.r2 != 0 &&
           actions.options != 0 && actions.touchpad_click != 0;
}

bool resolve_action_handles_worker() {
    if (action_handles_complete(g_steam.actions)) {
        return true;
    }

    const ULONGLONG now = GetTickCount64();
    if (now < g_steam.action_retry_after) {
        return false;
    }
    g_steam.action_retry_after = now + kSteamRetryMilliseconds;

    ActionHandles candidate{};
    candidate.action_set =
        g_steam.get_action_set_handle(g_steam.controller, "flower_ps4");
    candidate.left_stick =
        g_steam.get_analog_action_handle(g_steam.controller, "left_stick");
    candidate.right_stick =
        g_steam.get_analog_action_handle(g_steam.controller, "right_stick");
    candidate.tilt = g_steam.get_analog_action_handle(g_steam.controller, "tilt");
    candidate.dpad_up =
        g_steam.get_digital_action_handle(g_steam.controller, "dpad_up");
    candidate.dpad_right =
        g_steam.get_digital_action_handle(g_steam.controller, "dpad_right");
    candidate.dpad_down =
        g_steam.get_digital_action_handle(g_steam.controller, "dpad_down");
    candidate.dpad_left =
        g_steam.get_digital_action_handle(g_steam.controller, "dpad_left");
    candidate.square = g_steam.get_digital_action_handle(g_steam.controller, "square");
    candidate.cross = g_steam.get_digital_action_handle(g_steam.controller, "cross");
    candidate.circle = g_steam.get_digital_action_handle(g_steam.controller, "circle");
    candidate.triangle =
        g_steam.get_digital_action_handle(g_steam.controller, "triangle");
    candidate.l1 = g_steam.get_digital_action_handle(g_steam.controller, "l1");
    candidate.r1 = g_steam.get_digital_action_handle(g_steam.controller, "r1");
    candidate.l2 = g_steam.get_digital_action_handle(g_steam.controller, "l2");
    candidate.r2 = g_steam.get_digital_action_handle(g_steam.controller, "r2");
    candidate.options =
        g_steam.get_digital_action_handle(g_steam.controller, "options");
    candidate.touchpad_click =
        g_steam.get_digital_action_handle(g_steam.controller, "touchpad_click");

    const bool ready = action_handles_complete(candidate);
    if (ready) {
        g_steam.actions = candidate;
        debug_log("FlowerInput: resolved flower_ps4 action set and 17 actions\r\n");
    }
    return ready;
}

float clamp_unit(float value) {
    if (value < -1.0F) {
        return -1.0F;
    }
    if (value > 1.0F) {
        return 1.0F;
    }
    return value;
}

std::uint8_t pad_axis_value(float value) {
    const float scaled = (clamp_unit(value) + 1.0F) * 127.5F;
    return static_cast<std::uint8_t>(scaled + 0.5F);
}

bool tilt_acceleration_from_action(float x, float y, float output[3]) {
    if (output == nullptr || !std::isfinite(x) || !std::isfinite(y)) {
        return false;
    }

    const float roll = clamp_unit(x) * kTiltMaximumAngleRadians;
    const float pitch = clamp_unit(y) * kTiltMaximumAngleRadians;
    const float sine_roll = std::sin(roll);
    const float cosine_roll = std::cos(roll);
    const float sine_pitch = std::sin(pitch);
    const float cosine_pitch = std::cos(pitch);

    output[0] = sine_roll * cosine_pitch;
    output[1] = cosine_roll * cosine_pitch;
    output[2] = sine_pitch;
    return true;
}

void merge_digital_action(std::uint64_t steam_handle, std::uint64_t action_handle,
                          std::uint32_t button_mask, NamedActionSnapshot* snapshot) {
    const ControllerDigitalActionData data = g_steam.get_digital_action_data(
        g_steam.controller, steam_handle, action_handle);
    snapshot->active = snapshot->active || data.active;
    if (data.active && data.state) {
        snapshot->buttons |= button_mask;
    }
}

NamedActionSnapshot read_named_actions_worker(std::uint64_t steam_handle) {
    NamedActionSnapshot snapshot{};
    snapshot.acceleration[1] = 1.0F;

    g_steam.activate_action_set(g_steam.controller, steam_handle,
                                g_steam.actions.action_set);
    const ControllerAnalogActionData left_stick = g_steam.get_analog_action_data(
        g_steam.controller, steam_handle, g_steam.actions.left_stick);
    const ControllerAnalogActionData right_stick = g_steam.get_analog_action_data(
        g_steam.controller, steam_handle, g_steam.actions.right_stick);
    const ControllerAnalogActionData tilt = g_steam.get_analog_action_data(
        g_steam.controller, steam_handle, g_steam.actions.tilt);

    const bool left_stick_valid =
        left_stick.active && std::isfinite(left_stick.x) && std::isfinite(left_stick.y);
    const bool right_stick_valid = right_stick.active && std::isfinite(right_stick.x) &&
                                   std::isfinite(right_stick.y);
    const bool tilt_input_valid =
        tilt.active && std::isfinite(tilt.x) && std::isfinite(tilt.y);
    snapshot.active = left_stick_valid || right_stick_valid || tilt_input_valid;
    snapshot.left_stick_x = left_stick_valid ? clamp_unit(left_stick.x) : 0.0F;
    snapshot.left_stick_y = left_stick_valid ? clamp_unit(left_stick.y) : 0.0F;
    snapshot.right_stick_x = right_stick_valid ? clamp_unit(right_stick.x) : 0.0F;
    snapshot.right_stick_y = right_stick_valid ? clamp_unit(right_stick.y) : 0.0F;
    snapshot.tilt_valid =
        tilt_input_valid &&
        tilt_acceleration_from_action(tilt.x, tilt.y, snapshot.acceleration);

    merge_digital_action(steam_handle, g_steam.actions.dpad_up, kScePadButtonDpadUp,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.dpad_right,
                         kScePadButtonDpadRight, &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.dpad_down, kScePadButtonDpadDown,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.dpad_left, kScePadButtonDpadLeft,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.square, kScePadButtonSquare,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.cross, kScePadButtonCross,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.circle, kScePadButtonCircle,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.triangle, kScePadButtonTriangle,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.l1, kScePadButtonL1, &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.r1, kScePadButtonR1, &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.l2, kScePadButtonL2, &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.r2, kScePadButtonR2, &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.options, kScePadButtonOptions,
                         &snapshot);
    merge_digital_action(steam_handle, g_steam.actions.touchpad_click,
                         kScePadButtonTouchpad, &snapshot);
    return snapshot;
}

ScePadData state_from_actions(const NamedActionSnapshot& actions, ULONGLONG sample_tick,
                              std::uint8_t connected_count) {
    ScePadData state{};
    state.buttons = actions.buttons;
    state.left_stick_x = pad_axis_value(actions.left_stick_x);
    state.left_stick_y = pad_axis_value(actions.left_stick_y);
    state.right_stick_x = pad_axis_value(actions.right_stick_x);
    state.right_stick_y = pad_axis_value(actions.right_stick_y);
    state.orientation[3] = 1.0F;
    state.acceleration[0] = actions.tilt_valid ? actions.acceleration[0] : 0.0F;
    state.acceleration[1] = actions.tilt_valid ? actions.acceleration[1] : 1.0F;
    state.acceleration[2] = actions.tilt_valid ? actions.acceleration[2] : 0.0F;
    state.connected = 1;
    state.timestamp = sample_tick * UINT64_C(1000);
    state.connected_count = connected_count;
    return state;
}

bool handle_is_connected(std::uint64_t handle, const std::uint64_t* connected,
                         int count) {
    for (int index = 0; index < count; ++index) {
        if (connected[index] == handle) {
            return true;
        }
    }
    return false;
}

bool handle_is_assigned_locked(std::uint64_t handle) {
    for (const RuntimeSlot& slot : g_slots) {
        if (slot.open && slot.steam_handle == handle) {
            return true;
        }
    }
    return false;
}

void reset_output_memory_locked(RuntimeSlot& slot) {
    slot.vibration_known = false;
    slot.light_bar_known = false;
    slot.last_large_motor = 0;
    slot.last_small_motor = 0;
    slot.last_light_bar = {};
}

void advance_generation_locked(RuntimeSlot& slot) {
    ++slot.generation;
    if (slot.generation == 0) {
        ++slot.generation;
    }
}

std::uint64_t invalidate_owner_locked(RuntimeSlot& slot) {
    const std::uint64_t handle_to_stop =
        slot.owner_active ? slot.steam_handle : kInvalidControllerHandle;
    if (slot.owner_active || slot.state_valid) {
        advance_generation_locked(slot);
    }
    slot.owner_active = false;
    slot.state_valid = false;
    slot.published_tick = 0;
    reset_output_memory_locked(slot);
    return handle_to_stop;
}

OutputRequest* select_output_request_locked(std::uint64_t steam_handle) {
    OutputRequest* selected = nullptr;
    for (OutputRequest& request : g_output_requests) {
        if (request.occupied && request.target.steam_handle == steam_handle) {
            return &request;
        }
        if (!request.occupied && selected == nullptr) {
            selected = &request;
        }
    }
    if (selected == nullptr) {
        selected = &g_output_requests[kMaximumOutputRequests - 1];
    }
    if (selected->occupied) {
        *selected = {};
    }
    return selected;
}

bool same_output_target(const OutputTarget& left, const OutputTarget& right) {
    return left.slot_index == right.slot_index &&
           left.native_handle == right.native_handle &&
           left.steam_handle == right.steam_handle &&
           left.generation == right.generation;
}

void bind_output_request_locked(OutputRequest& request, const OutputTarget& target,
                                bool preserve_pending_stop) {
    const bool preserve_stop = preserve_pending_stop && request.occupied &&
                               !request.owner_bound && request.vibration_dirty &&
                               request.left_speed == 0 && request.right_speed == 0;
    if (request.occupied &&
        (!request.owner_bound || !same_output_target(request.target, target))) {
        request = {};
        request.vibration_dirty = preserve_stop;
    }
    request.occupied = true;
    request.owner_bound = true;
    request.target = target;
}

void wake_worker() {
    if (g_worker_wake_event != nullptr) {
        (void)SetEvent(g_worker_wake_event);
    }
}

void queue_vibration(const OutputTarget& target, std::uint16_t left_speed,
                     std::uint16_t right_speed) {
    if (target.steam_handle == kInvalidControllerHandle) {
        return;
    }
    AcquireSRWLockExclusive(&g_output_lock);
    OutputRequest* selected = select_output_request_locked(target.steam_handle);
    bind_output_request_locked(*selected, target, false);
    selected->left_speed = left_speed;
    selected->right_speed = right_speed;
    selected->vibration_dirty = true;
    ReleaseSRWLockExclusive(&g_output_lock);
    wake_worker();
}

void queue_light_bar(const OutputTarget& target, const ScePadLightBarParam& light_bar) {
    if (target.steam_handle == kInvalidControllerHandle) {
        return;
    }
    AcquireSRWLockExclusive(&g_output_lock);
    OutputRequest* selected = select_output_request_locked(target.steam_handle);
    // A lightbar-only request for a new owner must not erase the zero-rumble
    // request that terminates the previous owner's vibration.
    bind_output_request_locked(*selected, target, true);
    selected->light_bar = light_bar;
    selected->light_bar_dirty = true;
    ReleaseSRWLockExclusive(&g_output_lock);
    wake_worker();
}

void queue_stop_vibration(std::uint64_t steam_handle) {
    if (steam_handle == kInvalidControllerHandle) {
        return;
    }
    AcquireSRWLockExclusive(&g_output_lock);
    OutputRequest* selected = select_output_request_locked(steam_handle);
    *selected = {};
    selected->occupied = true;
    selected->target.steam_handle = steam_handle;
    selected->vibration_dirty = true;
    ReleaseSRWLockExclusive(&g_output_lock);
    wake_worker();
}

bool output_target_is_current(const OutputTarget& target) {
    if (target.slot_index < 0 || target.slot_index >= kPadSlots) {
        return false;
    }
    const ULONGLONG now = GetTickCount64();
    AcquireSRWLockShared(&g_state_lock);
    const RuntimeSlot& slot = g_slots[target.slot_index];
    const bool current = slot.open && slot.owner_active && slot.state_valid &&
                         slot.native_handle == target.native_handle &&
                         slot.steam_handle == target.steam_handle &&
                         slot.generation == target.generation &&
                         now >= slot.published_tick &&
                         now - slot.published_tick <= kStateFreshnessMilliseconds;
    ReleaseSRWLockShared(&g_state_lock);
    return current;
}

void drain_output_requests_worker() {
    OutputRequest requests[kMaximumOutputRequests]{};
    AcquireSRWLockExclusive(&g_output_lock);
    std::memcpy(requests, g_output_requests, sizeof(requests));
    std::memset(g_output_requests, 0, sizeof(g_output_requests));
    ReleaseSRWLockExclusive(&g_output_lock);

    for (const OutputRequest& request : requests) {
        if (!request.occupied ||
            request.target.steam_handle == kInvalidControllerHandle) {
            continue;
        }
        if (request.vibration_dirty && g_steam.trigger_vibration != nullptr &&
            (!request.owner_bound || output_target_is_current(request.target))) {
            g_steam.trigger_vibration(g_steam.controller, request.target.steam_handle,
                                      request.left_speed, request.right_speed);
        }
        if (request.light_bar_dirty && g_steam.set_led_color != nullptr &&
            request.owner_bound && output_target_is_current(request.target)) {
            g_steam.set_led_color(g_steam.controller, request.target.steam_handle,
                                  request.light_bar.red, request.light_bar.green,
                                  request.light_bar.blue, 0);
        }
    }
}

bool any_native_slots_open() {
    AcquireSRWLockShared(&g_state_lock);
    bool any_open = false;
    for (const RuntimeSlot& slot : g_slots) {
        if (slot.open) {
            any_open = true;
            break;
        }
    }
    ReleaseSRWLockShared(&g_state_lock);
    return any_open;
}

int collect_assignments(WorkerAssignment assignments[kPadSlots]) {
    int count = 0;
    AcquireSRWLockShared(&g_state_lock);
    for (int index = 0; index < kPadSlots; ++index) {
        const RuntimeSlot& slot = g_slots[index];
        if (slot.open && slot.steam_handle != kInvalidControllerHandle) {
            assignments[count++] = {index, slot.native_handle, slot.steam_handle,
                                    slot.generation};
        }
    }
    ReleaseSRWLockShared(&g_state_lock);
    return count;
}

void assign_handle_to_slot_locked(RuntimeSlot& slot, std::uint64_t handle) {
    slot.steam_handle = handle;
    slot.owner_active = false;
    slot.state_valid = false;
    slot.published_state = {};
    slot.published_tick = 0;
    advance_generation_locked(slot);
    reset_output_memory_locked(slot);
}

void reconcile_controller_assignments_worker(
    const std::uint64_t connected[kMaximumSteamControllers],
    const int preferred_indices[kMaximumSteamControllers], int connected_count) {
    AcquireSRWLockExclusive(&g_state_lock);
    for (RuntimeSlot& slot : g_slots) {
        if (!slot.open ||
            (slot.steam_handle != kInvalidControllerHandle &&
             !handle_is_connected(slot.steam_handle, connected, connected_count))) {
            if (slot.steam_handle != kInvalidControllerHandle) {
                const std::uint64_t owner_to_stop = invalidate_owner_locked(slot);
                if (owner_to_stop != kInvalidControllerHandle) {
                    queue_stop_vibration(owner_to_stop);
                }
                slot.steam_handle = kInvalidControllerHandle;
                advance_generation_locked(slot);
            }
        }
    }

    // Reserve exact Steam gamepad-index matches before assigning unindexed or
    // displaced handles to fallback slots. Enumeration order must not steal a
    // later controller's exact native slot.
    for (int connected_index = 0; connected_index < connected_count;
         ++connected_index) {
        const std::uint64_t handle = connected[connected_index];
        if (handle == kInvalidControllerHandle || handle_is_assigned_locked(handle)) {
            continue;
        }
        const int preferred = preferred_indices[connected_index];
        if (preferred >= 0 && preferred < kPadSlots && g_slots[preferred].open &&
            g_slots[preferred].steam_handle == kInvalidControllerHandle) {
            assign_handle_to_slot_locked(g_slots[preferred], handle);
        }
    }

    for (int connected_index = 0; connected_index < connected_count;
         ++connected_index) {
        const std::uint64_t handle = connected[connected_index];
        if (handle == kInvalidControllerHandle || handle_is_assigned_locked(handle)) {
            continue;
        }
        for (RuntimeSlot& slot : g_slots) {
            if (slot.open && slot.steam_handle == kInvalidControllerHandle) {
                assign_handle_to_slot_locked(slot, handle);
                break;
            }
        }
    }
    ReleaseSRWLockExclusive(&g_state_lock);
}

void invalidate_all_owners_worker(bool clear_assignments) {
    AcquireSRWLockExclusive(&g_state_lock);
    for (RuntimeSlot& slot : g_slots) {
        const std::uint64_t handle = invalidate_owner_locked(slot);
        if (handle != kInvalidControllerHandle) {
            queue_stop_vibration(handle);
        }
        if (clear_assignments && slot.steam_handle != kInvalidControllerHandle) {
            slot.steam_handle = kInvalidControllerHandle;
            advance_generation_locked(slot);
        }
    }
    ReleaseSRWLockExclusive(&g_state_lock);
}

void publish_worker_sample(const WorkerSample& sample) {
    bool became_active = false;

    AcquireSRWLockExclusive(&g_state_lock);
    if (sample.assignment.slot_index >= 0 && sample.assignment.slot_index < kPadSlots) {
        RuntimeSlot& slot = g_slots[sample.assignment.slot_index];
        if (slot.open && slot.native_handle == sample.assignment.native_handle &&
            slot.steam_handle == sample.assignment.steam_handle &&
            slot.generation == sample.assignment.generation) {
            if (sample.actions.active) {
                if (!slot.owner_active) {
                    ++slot.connected_count;
                    if (slot.connected_count == 0) {
                        ++slot.connected_count;
                    }
                    advance_generation_locked(slot);
                    became_active = true;
                }
                slot.owner_active = true;
                slot.state_valid = true;
                slot.published_tick = sample.sample_tick;
                slot.published_state = state_from_actions(
                    sample.actions, sample.sample_tick, slot.connected_count);
            } else {
                const std::uint64_t handle_to_stop = invalidate_owner_locked(slot);
                if (handle_to_stop != kInvalidControllerHandle) {
                    queue_stop_vibration(handle_to_stop);
                }
            }
        }
    }
    ReleaseSRWLockExclusive(&g_state_lock);

    if (became_active) {
        debug_log("FlowerInput: Steam actions now own a native ScePad slot\r\n");
    }
}

DWORD WINAPI steam_worker_thread(LPVOID) {
    debug_log("FlowerInput: native ScePad Steam worker started\r\n");
    for (;;) {
        const bool any_open = any_native_slots_open();
        const DWORD wait_interval = any_open ? kActiveWorkerIntervalMilliseconds
                                             : kIdleWorkerIntervalMilliseconds;
        if (g_worker_wake_event != nullptr) {
            (void)WaitForSingleObject(g_worker_wake_event, wait_interval);
        } else {
            Sleep(wait_interval);
        }

        if (!any_native_slots_open()) {
            if (g_steam.controller != nullptr) {
                drain_output_requests_worker();
            }
            continue;
        }

        if (!acquire_steam_controller_worker()) {
            invalidate_all_owners_worker(false);
            continue;
        }

        // Deliver requests before RunFrame so a delayed Steam poll cannot hold up
        // output queued by a Flower-facing wrapper.
        drain_output_requests_worker();
        if (!any_native_slots_open()) {
            continue;
        }

        // Only this worker calls SteamController. No Flower-facing ScePad lock is
        // held while Steam code executes, so a blocked Steam call cannot block the
        // game's native input thread.
        g_steam.run_frame(g_steam.controller);
        if (!any_native_slots_open()) {
            drain_output_requests_worker();
            continue;
        }

        std::uint64_t connected[kMaximumSteamControllers]{};
        int reported_count =
            g_steam.get_connected_controllers(g_steam.controller, connected);
        if (reported_count < 0) {
            reported_count = 0;
        }
        const int connected_count = reported_count > kMaximumSteamControllers
                                        ? kMaximumSteamControllers
                                        : reported_count;
        int preferred_indices[kMaximumSteamControllers]{};
        for (int index = 0; index < connected_count; ++index) {
            preferred_indices[index] =
                g_steam.get_gamepad_index(g_steam.controller, connected[index]);
        }
        reconcile_controller_assignments_worker(connected, preferred_indices,
                                                connected_count);

        const bool actions_ready = resolve_action_handles_worker();
        WorkerAssignment assignments[kPadSlots]{};
        const int assignment_count = collect_assignments(assignments);
        if (!actions_ready) {
            invalidate_all_owners_worker(false);
            drain_output_requests_worker();
            continue;
        }

        WorkerSample samples[kPadSlots]{};
        for (int index = 0; index < assignment_count; ++index) {
            samples[index].assignment = assignments[index];
            samples[index].sample_tick = GetTickCount64();
            samples[index].actions =
                read_named_actions_worker(assignments[index].steam_handle);
        }
        for (int index = 0; index < assignment_count; ++index) {
            publish_worker_sample(samples[index]);
        }
        drain_output_requests_worker();
    }
}

BOOL CALLBACK start_worker_once(PINIT_ONCE, PVOID, PVOID*) {
    wchar_t proxy_path[MAX_PATH]{};
    const DWORD path_length = GetModuleFileNameW(g_proxy_module, proxy_path, MAX_PATH);
    if (path_length == 0 || path_length >= MAX_PATH) {
        return FALSE;
    }

    // Keep this module loaded for the process lifetime. The worker intentionally
    // has no shutdown handshake because waiting under the loader lock is unsafe.
    g_worker_module_pin = LoadLibraryW(proxy_path);
    if (g_worker_module_pin == nullptr) {
        return FALSE;
    }

    g_worker_wake_event = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (g_worker_wake_event == nullptr) {
        return FALSE;
    }
    HANDLE thread = CreateThread(nullptr, 0, steam_worker_thread, nullptr, 0, nullptr);
    if (thread == nullptr) {
        CloseHandle(g_worker_wake_event);
        g_worker_wake_event = nullptr;
        return FALSE;
    }
    CloseHandle(thread);
    return TRUE;
}

bool ensure_worker_started() {
    return InitOnceExecuteOnce(&g_worker_once, start_worker_once, nullptr, nullptr) !=
           FALSE;
}

int preferred_slot_from_open(std::int32_t user_id, std::int32_t index) {
    if (user_id >= 1 && user_id <= kPadSlots) {
        return user_id - 1;
    }
    if (index >= 0 && index < kPadSlots) {
        return index;
    }
    return -1;
}

void record_open_handle(std::int32_t handle, std::int32_t user_id, std::int32_t index) {
    if (handle < 0) {
        return;
    }
    const int preferred = preferred_slot_from_open(user_id, index);
    if (preferred < 0) {
        return;
    }

    std::uint64_t handle_to_stop = kInvalidControllerHandle;
    AcquireSRWLockExclusive(&g_state_lock);
    RuntimeSlot& slot = g_slots[preferred];
    if (slot.open && slot.owner_active) {
        handle_to_stop = slot.steam_handle;
    }
    const std::uint64_t previous_generation = slot.generation;
    slot = {};
    slot.generation = previous_generation;
    advance_generation_locked(slot);
    slot.native_handle = handle;
    slot.preferred_index = preferred;
    slot.open = true;
    if (handle_to_stop != kInvalidControllerHandle) {
        queue_stop_vibration(handle_to_stop);
    }
    ReleaseSRWLockExclusive(&g_state_lock);

    if (ensure_worker_started()) {
        wake_worker();
    }
}

void record_closed_handle(std::int32_t handle) {
    std::uint64_t handle_to_stop = kInvalidControllerHandle;
    AcquireSRWLockExclusive(&g_state_lock);
    for (RuntimeSlot& slot : g_slots) {
        if (slot.open && slot.native_handle == handle) {
            handle_to_stop = slot.steam_handle;
            const std::uint64_t previous_generation = slot.generation;
            slot = {};
            slot.generation = previous_generation;
            advance_generation_locked(slot);
            slot.native_handle = -1;
            slot.preferred_index = -1;
            if (handle_to_stop != kInvalidControllerHandle) {
                queue_stop_vibration(handle_to_stop);
            }
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_state_lock);
    wake_worker();
}

bool copy_fresh_steam_state(std::int32_t handle, ScePadData* output) {
    if (output == nullptr) {
        return false;
    }

    const ULONGLONG now = GetTickCount64();
    std::uint64_t handle_to_stop = kInvalidControllerHandle;
    bool copied = false;
    AcquireSRWLockExclusive(&g_state_lock);
    for (RuntimeSlot& slot : g_slots) {
        if (!slot.open || slot.native_handle != handle) {
            continue;
        }
        const bool fresh = slot.owner_active && slot.state_valid &&
                           slot.steam_handle != kInvalidControllerHandle &&
                           now >= slot.published_tick &&
                           now - slot.published_tick <= kStateFreshnessMilliseconds;
        if (fresh) {
            *output = slot.published_state;
            copied = true;
        } else if (slot.owner_active || slot.state_valid) {
            handle_to_stop = invalidate_owner_locked(slot);
            if (handle_to_stop != kInvalidControllerHandle) {
                queue_stop_vibration(handle_to_stop);
            }
        }
        break;
    }
    ReleaseSRWLockExclusive(&g_state_lock);
    return copied;
}

bool route_steam_vibration(std::int32_t handle, const ScePadVibrationParam& vibration) {
    const ULONGLONG now = GetTickCount64();
    bool routed = false;
    AcquireSRWLockExclusive(&g_state_lock);
    for (int index = 0; index < kPadSlots; ++index) {
        RuntimeSlot& slot = g_slots[index];
        if (!slot.open || slot.native_handle != handle) {
            continue;
        }
        const bool fresh = slot.owner_active && slot.state_valid &&
                           now >= slot.published_tick &&
                           now - slot.published_tick <= kStateFreshnessMilliseconds;
        if (fresh) {
            routed = true;
            const bool changed = !slot.vibration_known ||
                                 slot.last_large_motor != vibration.large_motor ||
                                 slot.last_small_motor != vibration.small_motor;
            if (changed) {
                const OutputTarget target = {index, slot.native_handle,
                                             slot.steam_handle, slot.generation};
                queue_vibration(
                    target,
                    static_cast<std::uint16_t>(vibration.large_motor) * UINT16_C(257),
                    static_cast<std::uint16_t>(vibration.small_motor) * UINT16_C(257));
                slot.last_large_motor = vibration.large_motor;
                slot.last_small_motor = vibration.small_motor;
                slot.vibration_known = true;
            }
        } else if (slot.owner_active || slot.state_valid) {
            const std::uint64_t handle_to_stop = invalidate_owner_locked(slot);
            if (handle_to_stop != kInvalidControllerHandle) {
                queue_stop_vibration(handle_to_stop);
            }
        }
        break;
    }
    ReleaseSRWLockExclusive(&g_state_lock);
    return routed;
}

bool route_steam_light_bar(std::int32_t handle, const ScePadLightBarParam& light_bar) {
    const ULONGLONG now = GetTickCount64();
    bool routed = false;
    AcquireSRWLockExclusive(&g_state_lock);
    for (int index = 0; index < kPadSlots; ++index) {
        RuntimeSlot& slot = g_slots[index];
        if (!slot.open || slot.native_handle != handle) {
            continue;
        }
        const bool fresh = slot.owner_active && slot.state_valid &&
                           now >= slot.published_tick &&
                           now - slot.published_tick <= kStateFreshnessMilliseconds;
        if (fresh) {
            routed = true;
            const bool changed =
                !slot.light_bar_known ||
                std::memcmp(&slot.last_light_bar, &light_bar, sizeof(light_bar)) != 0;
            if (changed) {
                const OutputTarget target = {index, slot.native_handle,
                                             slot.steam_handle, slot.generation};
                queue_light_bar(target, light_bar);
                slot.last_light_bar = light_bar;
                slot.light_bar_known = true;
            }
        } else if (slot.owner_active || slot.state_valid) {
            const std::uint64_t handle_to_stop = invalidate_owner_locked(slot);
            if (handle_to_stop != kInvalidControllerHandle) {
                queue_stop_vibration(handle_to_stop);
            }
        }
        break;
    }
    ReleaseSRWLockExclusive(&g_state_lock);
    return routed;
}

} // namespace

extern "C" std::int32_t scePadOpen(std::int32_t user_id, std::int32_t type,
                                   std::int32_t index, const void* parameters) {
    if (!load_original_api()) {
        return kScePadErrorFatal;
    }
    const std::int32_t handle = g_original.open(user_id, type, index, parameters);
    record_open_handle(handle, user_id, index);
    return handle;
}

extern "C" std::int32_t scePadClose(std::int32_t handle) {
    if (!load_original_api()) {
        return kScePadErrorFatal;
    }
    const std::int32_t result = g_original.close(handle);
    if (result == 0) {
        record_closed_handle(handle);
    }
    return result;
}

extern "C" std::int32_t scePadReadState(std::int32_t handle, ScePadData* data) {
    if (!load_original_api()) {
        return kScePadErrorFatal;
    }
    if (copy_fresh_steam_state(handle, data)) {
        return 0;
    }
    return g_original.read_state(handle, data);
}

extern "C" std::int32_t scePadSetVibration(std::int32_t handle,
                                           const ScePadVibrationParam* vibration) {
    if (!load_original_api()) {
        return kScePadErrorFatal;
    }
    if (vibration == nullptr) {
        return g_original.set_vibration(handle, vibration);
    }

    if (route_steam_vibration(handle, *vibration)) {
        return 0;
    }
    return g_original.set_vibration(handle, vibration);
}

extern "C" std::int32_t scePadSetLightBar(std::int32_t handle,
                                          const ScePadLightBarParam* light_bar) {
    if (!load_original_api()) {
        return kScePadErrorFatal;
    }
    if (light_bar == nullptr) {
        return g_original.set_light_bar(handle, light_bar);
    }

    if (route_steam_light_bar(handle, *light_bar)) {
        return 0;
    }
    return g_original.set_light_bar(handle, light_bar);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_proxy_module = instance;
        for (RuntimeSlot& slot : g_slots) {
            slot.native_handle = -1;
            slot.preferred_index = -1;
        }
        DisableThreadLibraryCalls(instance);
    }
    return TRUE;
}
