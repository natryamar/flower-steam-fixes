#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>

namespace {

constexpr std::uint32_t kOptions = UINT32_C(0x00000008);
constexpr std::uint32_t kDpadUp = UINT32_C(0x00000010);
constexpr std::uint32_t kDpadRight = UINT32_C(0x00000020);
constexpr std::uint32_t kDpadDown = UINT32_C(0x00000040);
constexpr std::uint32_t kDpadLeft = UINT32_C(0x00000080);
constexpr std::uint32_t kL2 = UINT32_C(0x00000100);
constexpr std::uint32_t kR2 = UINT32_C(0x00000200);
constexpr std::uint32_t kL1 = UINT32_C(0x00000400);
constexpr std::uint32_t kR1 = UINT32_C(0x00000800);
constexpr std::uint32_t kTriangle = UINT32_C(0x00001000);
constexpr std::uint32_t kCircle = UINT32_C(0x00002000);
constexpr std::uint32_t kCross = UINT32_C(0x00004000);
constexpr std::uint32_t kSquare = UINT32_C(0x00008000);
constexpr std::uint32_t kTouchpad = UINT32_C(0x00100000);
constexpr std::uint32_t kAllSupportedButtons =
    kOptions | kDpadUp | kDpadRight | kDpadDown | kDpadLeft | kL2 | kR2 | kL1 | kR1 |
    kTriangle | kCircle | kCross | kSquare | kTouchpad;
constexpr std::uint64_t kFirstController = 42;

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

static_assert(sizeof(ScePadData) == 0x78);
static_assert(sizeof(ScePadVibrationParam) == 2);
static_assert(sizeof(ScePadLightBarParam) == 3);

using SteamInitFunction = bool (*)();
using SteamShutdownFunction = void (*)();
using ResetFunction = void (*)();
using SetConnectedCountFunction = void (*)(int);
using SetEnumerationFunction = void (*)(BOOL);
using SetGamepadIndexFunction = void (*)(int, int);
using SetDelayFunction = void (*)(DWORD);
using SetActiveFunction = void (*)(int, BOOL);
using SetAnalogFunction = void (*)(int, float, float);
using SetButtonsFunction = void (*)(int, std::uint32_t);
using GetCountFunction = LONG (*)();
using GetUint64Function = std::uint64_t (*)();
using GetUint16Function = std::uint16_t (*)();
using GetUint32Function = std::uint32_t (*)();

using InitFunction = std::int32_t (*)();
using OpenFunction = std::int32_t (*)(std::int32_t, std::int32_t, std::int32_t,
                                      const void*);
using CloseFunction = std::int32_t (*)(std::int32_t);
using ReadFunction = std::int32_t (*)(std::int32_t, ScePadData*);
using SetVibrationFunction = std::int32_t (*)(std::int32_t,
                                              const ScePadVibrationParam*);
using SetLightBarFunction = std::int32_t (*)(std::int32_t, const ScePadLightBarParam*);

struct SteamControls {
    ResetFunction reset;
    SetConnectedCountFunction set_connected_count;
    SetEnumerationFunction set_enumeration_reversed;
    SetGamepadIndexFunction set_gamepad_index;
    SetDelayFunction set_run_frame_delay;
    SetDelayFunction set_vibration_delay;
    SetActiveFunction set_surface_active;
    SetActiveFunction set_tilt_active;
    SetAnalogFunction set_left_stick;
    SetAnalogFunction set_right_stick;
    SetAnalogFunction set_tilt;
    SetButtonsFunction set_buttons;
    GetCountFunction controller_calls;
    GetCountFunction run_frame_count;
    GetCountFunction motion_calls;
    GetCountFunction vibration_entries;
    GetCountFunction vibration_calls;
    GetCountFunction led_calls;
    GetUint64Function last_output_handle;
    GetUint16Function last_vibration_left;
    GetUint16Function last_vibration_right;
    GetUint32Function last_led_rgb;
};

struct OriginalControls {
    ResetFunction reset;
    GetCountFunction read_count;
    GetCountFunction vibration_count;
    GetCountFunction light_bar_count;
    GetUint16Function last_vibration;
    GetUint32Function last_light_bar;
};

template <typename Function> Function load_export(HMODULE module, const char* name) {
    return reinterpret_cast<Function>(GetProcAddress(module, name));
}

bool make_result_path(wchar_t* path, DWORD capacity) {
    const DWORD length = GetModuleFileNameW(nullptr, path, capacity);
    if (length == 0 || length >= capacity) {
        return false;
    }
    wchar_t* separator = std::wcsrchr(path, L'\\');
    if (separator == nullptr) {
        return false;
    }
    ++separator;
    const std::size_t remaining = capacity - static_cast<std::size_t>(separator - path);
    return wcscpy_s(separator, remaining, L"native_scepad_smoke_result.txt") == 0;
}

void record_stage(const char* message) {
    std::printf("%s\n", message);
    std::fflush(stdout);

    wchar_t path[MAX_PATH]{};
    if (!make_result_path(path, MAX_PATH)) {
        return;
    }
    HANDLE file =
        CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                    OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        return;
    }
    DWORD written = 0;
    (void)WriteFile(file, message, static_cast<DWORD>(std::strlen(message)), &written,
                    nullptr);
    constexpr char newline[] = "\r\n";
    (void)WriteFile(file, newline, 2, &written, nullptr);
    CloseHandle(file);
}

bool controls_complete(const SteamControls& controls) {
    return controls.reset != nullptr && controls.set_connected_count != nullptr &&
           controls.set_enumeration_reversed != nullptr &&
           controls.set_gamepad_index != nullptr &&
           controls.set_run_frame_delay != nullptr &&
           controls.set_vibration_delay != nullptr &&
           controls.set_surface_active != nullptr &&
           controls.set_tilt_active != nullptr && controls.set_left_stick != nullptr &&
           controls.set_right_stick != nullptr && controls.set_tilt != nullptr &&
           controls.set_buttons != nullptr && controls.controller_calls != nullptr &&
           controls.run_frame_count != nullptr && controls.motion_calls != nullptr &&
           controls.vibration_entries != nullptr &&
           controls.vibration_calls != nullptr && controls.led_calls != nullptr &&
           controls.last_output_handle != nullptr &&
           controls.last_vibration_left != nullptr &&
           controls.last_vibration_right != nullptr && controls.last_led_rgb != nullptr;
}

bool controls_complete(const OriginalControls& controls) {
    return controls.reset != nullptr && controls.read_count != nullptr &&
           controls.vibration_count != nullptr && controls.light_bar_count != nullptr &&
           controls.last_vibration != nullptr && controls.last_light_bar != nullptr;
}

bool nearly_equal(float left, float right, float tolerance = 0.0001F) {
    return std::fabs(left - right) <= tolerance;
}

bool bytes_are_zero(const std::uint8_t* data, std::size_t size) {
    for (std::size_t index = 0; index < size; ++index) {
        if (data[index] != 0) {
            return false;
        }
    }
    return true;
}

bool is_original_marker(const ScePadData& state) {
    return state.buttons == UINT32_C(0x00ABCDEF) && state.left_stick_x == 11 &&
           state.left_stick_y == 22 && state.right_stick_x == 33 &&
           state.right_stick_y == 44 && state.left_trigger == 55 &&
           state.right_trigger == 66 && nearly_equal(state.acceleration[0], 5.0F) &&
           nearly_equal(state.acceleration[1], 6.0F) &&
           nearly_equal(state.acceleration[2], 7.0F) && state.connected == 0 &&
           state.timestamp == UINT64_C(0x1122334455667788);
}

bool is_complete_synthetic(const ScePadData& state, std::uint32_t buttons,
                           std::uint8_t left_x, std::uint8_t left_y,
                           std::uint8_t right_x, std::uint8_t right_y,
                           float acceleration_x, float acceleration_y,
                           float acceleration_z, std::uint8_t connected_count) {
    return state.buttons == buttons && state.left_stick_x == left_x &&
           state.left_stick_y == left_y && state.right_stick_x == right_x &&
           state.right_stick_y == right_y && state.left_trigger == 0 &&
           state.right_trigger == 0 &&
           bytes_are_zero(state.alignment_0, sizeof(state.alignment_0)) &&
           nearly_equal(state.orientation[0], 0.0F) &&
           nearly_equal(state.orientation[1], 0.0F) &&
           nearly_equal(state.orientation[2], 0.0F) &&
           nearly_equal(state.orientation[3], 1.0F) &&
           nearly_equal(state.acceleration[0], acceleration_x) &&
           nearly_equal(state.acceleration[1], acceleration_y) &&
           nearly_equal(state.acceleration[2], acceleration_z) &&
           nearly_equal(state.angular_velocity[0], 0.0F) &&
           nearly_equal(state.angular_velocity[1], 0.0F) &&
           nearly_equal(state.angular_velocity[2], 0.0F) &&
           bytes_are_zero(state.touch_data, sizeof(state.touch_data)) &&
           state.connected == 1 &&
           bytes_are_zero(state.alignment_1, sizeof(state.alignment_1)) &&
           state.timestamp != 0 &&
           bytes_are_zero(state.extension_data, sizeof(state.extension_data)) &&
           state.connected_count == connected_count &&
           bytes_are_zero(state.reserved, sizeof(state.reserved));
}

template <typename Predicate> bool wait_until(Predicate predicate, DWORD timeout_ms) {
    const ULONGLONG started = GetTickCount64();
    do {
        if (predicate()) {
            return true;
        }
        Sleep(5);
    } while (GetTickCount64() - started < timeout_ms);
    return predicate();
}

template <typename Predicate>
bool wait_for_state(ReadFunction read, std::int32_t handle, Predicate predicate,
                    ScePadData* observed, DWORD timeout_ms = 2000) {
    ScePadData latest{};
    const bool matched = wait_until(
        [&]() {
            latest = {};
            return read(handle, &latest) == 0 && predicate(latest);
        },
        timeout_ms);
    if (observed != nullptr) {
        *observed = latest;
    }
    return matched;
}

} // namespace

int main() {
    wchar_t result_path[MAX_PATH]{};
    if (make_result_path(result_path, MAX_PATH)) {
        (void)DeleteFileW(result_path);
    }
    record_stage("start");

    HMODULE steam_module = LoadLibraryW(L"steam_api64.dll");
    HMODULE original_module = LoadLibraryW(L"libScePad_original.dll");
    if (steam_module == nullptr || original_module == nullptr) {
        record_stage("fake dependency load failed");
        return 1;
    }

    const auto steam_initialize =
        load_export<SteamInitFunction>(steam_module, "SteamAPI_Init");
    const auto steam_shutdown =
        load_export<SteamShutdownFunction>(steam_module, "SteamAPI_Shutdown");
    SteamControls steam{};
    steam.reset = load_export<ResetFunction>(steam_module, "FlowerFakeSteamReset");
    steam.set_connected_count = load_export<SetConnectedCountFunction>(
        steam_module, "FlowerFakeSteamSetConnectedCount");
    steam.set_enumeration_reversed = load_export<SetEnumerationFunction>(
        steam_module, "FlowerFakeSteamSetEnumerationReversed");
    steam.set_gamepad_index = load_export<SetGamepadIndexFunction>(
        steam_module, "FlowerFakeSteamSetGamepadIndex");
    steam.set_run_frame_delay =
        load_export<SetDelayFunction>(steam_module, "FlowerFakeSteamSetRunFrameDelay");
    steam.set_vibration_delay =
        load_export<SetDelayFunction>(steam_module, "FlowerFakeSteamSetVibrationDelay");
    steam.set_surface_active =
        load_export<SetActiveFunction>(steam_module, "FlowerFakeSteamSetSurfaceActive");
    steam.set_tilt_active =
        load_export<SetActiveFunction>(steam_module, "FlowerFakeSteamSetTiltActive");
    steam.set_left_stick = load_export<SetAnalogFunction>(
        steam_module, "FlowerFakeSteamSetLeftStickValues");
    steam.set_right_stick = load_export<SetAnalogFunction>(
        steam_module, "FlowerFakeSteamSetRightStickValues");
    steam.set_tilt =
        load_export<SetAnalogFunction>(steam_module, "FlowerFakeSteamSetTiltValues");
    steam.set_buttons =
        load_export<SetButtonsFunction>(steam_module, "FlowerFakeSteamSetButtons");
    steam.controller_calls = load_export<GetCountFunction>(
        steam_module, "FlowerFakeSteamGetControllerCallCount");
    steam.run_frame_count =
        load_export<GetCountFunction>(steam_module, "FlowerFakeSteamGetRunFrameCount");
    steam.motion_calls = load_export<GetCountFunction>(
        steam_module, "FlowerFakeSteamGetMotionCallCount");
    steam.vibration_entries = load_export<GetCountFunction>(
        steam_module, "FlowerFakeSteamGetVibrationEntryCount");
    steam.vibration_calls = load_export<GetCountFunction>(
        steam_module, "FlowerFakeSteamGetVibrationCallCount");
    steam.led_calls =
        load_export<GetCountFunction>(steam_module, "FlowerFakeSteamGetLedCallCount");
    steam.last_output_handle = load_export<GetUint64Function>(
        steam_module, "FlowerFakeSteamGetLastOutputHandle");
    steam.last_vibration_left = load_export<GetUint16Function>(
        steam_module, "FlowerFakeSteamGetLastVibrationLeft");
    steam.last_vibration_right = load_export<GetUint16Function>(
        steam_module, "FlowerFakeSteamGetLastVibrationRight");
    steam.last_led_rgb =
        load_export<GetUint32Function>(steam_module, "FlowerFakeSteamGetLastLedRgb");

    OriginalControls original{};
    original.reset =
        load_export<ResetFunction>(original_module, "FlowerFakeScePadReset");
    original.read_count =
        load_export<GetCountFunction>(original_module, "FlowerFakeScePadGetReadCount");
    original.vibration_count = load_export<GetCountFunction>(
        original_module, "FlowerFakeScePadGetVibrationCount");
    original.light_bar_count = load_export<GetCountFunction>(
        original_module, "FlowerFakeScePadGetLightBarCount");
    original.last_vibration = load_export<GetUint16Function>(
        original_module, "FlowerFakeScePadGetLastVibration");
    original.last_light_bar = load_export<GetUint32Function>(
        original_module, "FlowerFakeScePadGetLastLightBar");

    if (steam_initialize == nullptr || steam_shutdown == nullptr ||
        !controls_complete(steam) || !controls_complete(original)) {
        record_stage("fake control export missing");
        return 2;
    }
    steam.reset();
    original.reset();
    if (!steam_initialize()) {
        record_stage("SteamAPI_Init failed");
        return 3;
    }

    HMODULE bridge_module = LoadLibraryW(L"libScePad.dll");
    if (bridge_module == nullptr) {
        record_stage("bridge load failed");
        return 4;
    }
    const auto initialize = load_export<InitFunction>(bridge_module, "scePadInit");
    const auto open = load_export<OpenFunction>(bridge_module, "scePadOpen");
    const auto close = load_export<CloseFunction>(bridge_module, "scePadClose");
    const auto read = load_export<ReadFunction>(bridge_module, "scePadReadState");
    const auto set_vibration =
        load_export<SetVibrationFunction>(bridge_module, "scePadSetVibration");
    const auto set_light_bar =
        load_export<SetLightBarFunction>(bridge_module, "scePadSetLightBar");
    if (initialize == nullptr || open == nullptr || close == nullptr ||
        read == nullptr || set_vibration == nullptr || set_light_bar == nullptr) {
        record_stage("bridge export missing");
        return 5;
    }

    const std::int32_t init_result = initialize();
    const std::int32_t first_handle = open(1, 0, 0, nullptr);
    const std::int32_t second_handle = open(2, 0, 0, nullptr);
    if (init_result != 0 || first_handle < 0 || second_handle < 0) {
        record_stage("native open failed");
        return 6;
    }

    ScePadData first_state{};
    const bool independent_native_delivery = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.0F, 1.0F, 0.0F, 1);
        },
        &first_state);
    const LONG reads_before_authoritative = original.read_count();
    ScePadData authoritative_state{};
    const bool authoritative_read =
        read(first_handle, &authoritative_state) == 0 &&
        is_complete_synthetic(authoritative_state, kCross | kOptions, 191, 96, 32, 223,
                              0.0F, 1.0F, 0.0F, 1) &&
        original.read_count() == reads_before_authoritative;

    ScePadData second_fallback{};
    const bool initial_slot_isolation = read(second_handle, &second_fallback) == 0 &&
                                        is_original_marker(second_fallback);

    steam.set_connected_count(2);
    ScePadData second_state{};
    const bool two_slot_mapping = wait_for_state(
        read, second_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCircle | kTouchpad, 64, 159, 159, 64,
                                         0.0F, 1.0F, 0.0F, 1);
        },
        &second_state);

    steam.set_buttons(0, kAllSupportedButtons);
    const bool complete_button_surface = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kAllSupportedButtons, 191, 96, 32, 223,
                                         0.0F, 1.0F, 0.0F, 1);
        },
        nullptr);
    // D-pad actions are represented only by button bits; neither stick changes.
    steam.set_buttons(0, kCross | kOptions);

    steam.set_tilt(0, 0.75F, 0.25F);
    const bool action_drives_tilt = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.54489511F, 0.81549317F, 0.19509032F, 1);
        },
        nullptr);

    steam.set_tilt(0, 3.0F, 4.0F);
    const bool independent_angle_clamping = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.5F, 0.5F, 0.70710678F, 1);
        },
        nullptr);

    steam.set_surface_active(0, FALSE);
    steam.set_tilt(0, -0.5F, -0.5F);
    const bool inactive_actions_are_neutral = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, 0, 128, 128, 128, 128,
                                         -0.35355339F, 0.85355339F, -0.38268343F, 1);
        },
        nullptr);

    steam.set_tilt_active(0, FALSE);
    ScePadData generic_state{};
    const bool generic_full_fallback = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) { return is_original_marker(state); },
        &generic_state);

    steam.set_surface_active(0, TRUE);
    steam.set_tilt_active(0, TRUE);
    steam.set_tilt(0, 0.0F, 0.0F);
    const bool action_recovery = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.0F, 1.0F, 0.0F, 2);
        },
        nullptr);


    const LONG original_vibration_before = original.vibration_count();
    const LONG steam_vibration_before = steam.vibration_calls();
    ScePadVibrationParam vibration{4, 8};
    const bool vibration_returned = set_vibration(first_handle, &vibration) == 0;
    const bool native_vibration_routed =
        vibration_returned &&
        wait_until([&]() { return steam.vibration_calls() > steam_vibration_before; },
                   1000) &&
        steam.last_output_handle() == kFirstController &&
        steam.last_vibration_left() == 4U * 257U &&
        steam.last_vibration_right() == 8U * 257U &&
        original.vibration_count() == original_vibration_before;
    const LONG vibration_after_first = steam.vibration_calls();
    const bool repeated_vibration_returned =
        set_vibration(first_handle, &vibration) == 0;
    Sleep(40);
    const bool vibration_deduplicated =
        repeated_vibration_returned && steam.vibration_calls() == vibration_after_first;

    const LONG original_light_before = original.light_bar_count();
    const LONG steam_led_before = steam.led_calls();
    ScePadLightBarParam light_bar{10, 20, 30};
    const bool light_returned = set_light_bar(first_handle, &light_bar) == 0;
    const bool native_light_routed =
        light_returned &&
        wait_until([&]() { return steam.led_calls() > steam_led_before; }, 1000) &&
        steam.last_output_handle() == kFirstController &&
        steam.last_led_rgb() == UINT32_C(0x000A141E) &&
        original.light_bar_count() == original_light_before;

    steam.set_surface_active(0, FALSE);
    steam.set_tilt_active(0, FALSE);
    const bool fallback_before_native_outputs = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) { return is_original_marker(state); }, nullptr);
    Sleep(40);
    const LONG steam_vibration_before_fallback = steam.vibration_calls();
    const LONG original_vibration_before_fallback = original.vibration_count();
    ScePadVibrationParam fallback_vibration{9, 7};
    const bool original_vibration_fallback =
        set_vibration(first_handle, &fallback_vibration) == 0 &&
        original.vibration_count() == original_vibration_before_fallback + 1 &&
        original.last_vibration() == UINT16_C(0x0709);
    Sleep(40);
    const bool fallback_did_not_route_vibration =
        steam.vibration_calls() == steam_vibration_before_fallback;

    const LONG original_light_before_fallback = original.light_bar_count();
    ScePadLightBarParam fallback_light{1, 2, 3};
    const bool original_light_fallback =
        set_light_bar(first_handle, &fallback_light) == 0 &&
        original.light_bar_count() == original_light_before_fallback + 1 &&
        original.last_light_bar() == UINT32_C(0x00010203);

    steam.set_connected_count(0);
    const bool disconnect_fallback = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) { return is_original_marker(state); }, nullptr);
    steam.set_connected_count(1);
    steam.set_surface_active(0, TRUE);
    steam.set_tilt_active(0, TRUE);
    const bool reconnect = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.0F, 1.0F, 0.0F, 3);
        },
        nullptr);

    const LONG run_frames_before_block = steam.run_frame_count();
    steam.set_run_frame_delay(600);
    const bool worker_entered_block = wait_until(
        [&]() { return steam.run_frame_count() > run_frames_before_block; }, 1000);
    Sleep(300);
    // Exercise the native output wrapper first: it must detect stale ownership
    // itself rather than relying on a prior read to invalidate the slot.
    const LONG original_vibration_before_block = original.vibration_count();
    const ULONGLONG blocked_output_started = GetTickCount64();
    const std::int32_t blocked_output_result =
        set_vibration(first_handle, &fallback_vibration);
    const ULONGLONG blocked_output_elapsed = GetTickCount64() - blocked_output_started;
    const bool blocked_worker_does_not_block_output =
        blocked_output_result == 0 && blocked_output_elapsed < 50 &&
        original.vibration_count() == original_vibration_before_block + 1;

    ScePadData stale_state{};
    const ULONGLONG stale_started = GetTickCount64();
    const std::int32_t stale_result = read(first_handle, &stale_state);
    const ULONGLONG stale_elapsed = GetTickCount64() - stale_started;
    const bool blocked_worker_does_not_block_read =
        worker_entered_block && stale_result == 0 && stale_elapsed < 50 &&
        is_original_marker(stale_state);

    steam.set_run_frame_delay(0);
    const bool worker_recovery = wait_for_state(
        read, first_handle,
        [](const ScePadData& state) {
            return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                         0.0F, 1.0F, 0.0F, 4);
        },
        nullptr, 2500);

    // An unindexed controller enumerated first must not consume a later
    // controller's exact gamepad-index slot.
    steam.set_connected_count(0);
    const bool priority_disconnect =
        wait_for_state(
            read, first_handle,
            [](const ScePadData& state) { return is_original_marker(state); },
            nullptr) &&
        wait_for_state(
            read, second_handle,
            [](const ScePadData& state) { return is_original_marker(state); }, nullptr);
    steam.set_enumeration_reversed(TRUE);
    steam.set_gamepad_index(0, 0);
    steam.set_gamepad_index(1, -1);
    steam.set_connected_count(2);
    const bool exact_index_priority =
        priority_disconnect &&
        wait_for_state(
            read, first_handle,
            [](const ScePadData& state) {
                return is_complete_synthetic(state, kCross | kOptions, 191, 96, 32, 223,
                                             0.0F, 1.0F, 0.0F, 5);
            },
            nullptr) &&
        wait_for_state(
            read, second_handle,
            [](const ScePadData& state) {
                return is_complete_synthetic(state, kCircle | kTouchpad, 64, 159, 159,
                                             64, 0.0F, 1.0F, 0.0F, 2);
            },
            nullptr);

    // Force the worker to copy a vibration+light request, block in vibration,
    // then close the owning slot. The copied light request must fail its second
    // ownership check, and the queued stop must replace any pending payload.
    const LONG run_frames_before_output_race = steam.run_frame_count();
    steam.set_run_frame_delay(100);
    const bool output_race_poll_started = wait_until(
        [&]() { return steam.run_frame_count() > run_frames_before_output_race; },
        1000);
    const LONG vibration_entries_before_close = steam.vibration_entries();
    const LONG vibration_calls_before_close = steam.vibration_calls();
    const LONG led_calls_before_close = steam.led_calls();
    steam.set_vibration_delay(600);
    ScePadVibrationParam closing_vibration{33, 44};
    ScePadLightBarParam closing_light{90, 80, 70};
    const bool closing_outputs_queued =
        set_vibration(first_handle, &closing_vibration) == 0 &&
        set_light_bar(first_handle, &closing_light) == 0;
    steam.set_run_frame_delay(0);
    const bool vibration_call_blocked = wait_until(
        [&]() { return steam.vibration_entries() > vibration_entries_before_close; },
        1000);
    const bool first_close_ok = close(first_handle) == 0;
    steam.set_vibration_delay(0);
    const bool blocked_vibration_completed = wait_until(
        [&]() { return steam.vibration_calls() > vibration_calls_before_close; }, 1500);
    const bool stop_vibration_completed = wait_until(
        [&]() { return steam.vibration_calls() > vibration_calls_before_close + 1; },
        1500);
    const bool close_cancels_stale_output =
        output_race_poll_started && closing_outputs_queued && vibration_call_blocked &&
        first_close_ok && blocked_vibration_completed && stop_vibration_completed &&
        steam.led_calls() == led_calls_before_close &&
        steam.last_vibration_left() == 0 && steam.last_vibration_right() == 0;

    const bool no_raw_motion = steam.motion_calls() == 0;
    const bool steam_worker_was_used =
        steam.run_frame_count() > 0 && steam.controller_calls() > 0;
    const LONG vibration_before_second_close = steam.vibration_calls();
    const bool second_close_ok = close(second_handle) == 0;
    const bool second_stop_completed = wait_until(
        [&]() { return steam.vibration_calls() > vibration_before_second_close; },
        1000);
    const bool close_ok = first_close_ok && second_close_ok && second_stop_completed;

    const bool passed =
        independent_native_delivery && authoritative_read && initial_slot_isolation &&
        two_slot_mapping && complete_button_surface && action_drives_tilt &&
        independent_angle_clamping && inactive_actions_are_neutral &&
        generic_full_fallback && action_recovery && native_vibration_routed &&
        vibration_deduplicated &&
        native_light_routed && fallback_before_native_outputs &&
        original_vibration_fallback && fallback_did_not_route_vibration &&
        original_light_fallback && disconnect_fallback && reconnect &&
        blocked_worker_does_not_block_read && blocked_worker_does_not_block_output &&
        worker_recovery && exact_index_priority && close_cancels_stale_output &&
        no_raw_motion && steam_worker_was_used && close_ok;

    char summary[2000]{};
    (void)std::snprintf(
        summary, sizeof(summary),
        "native_no_xinput=%d authoritative=%d slot_isolation=%d two_slots=%d "
        "raw_buttons=%d angle_tilt=%d angle_clamp=%d inactive_neutral=%d "
        "generic_fallback=%d recovery=%d native_vibration=%d vibration_dedupe=%d "
        "native_light=%d "
        "fallback_ready=%d original_vibration=%d no_fallback_vibration_route=%d "
        "original_light=%d disconnect=%d reconnect=%d blocked_read=%d/%llu_ms "
        "blocked_output=%d/%llu_ms worker_recovery=%d index_priority=%d "
        "close_cancels_output=%d no_raw_motion=%d worker_calls=%ld close=%d "
        "pass=%d",
        independent_native_delivery ? 1 : 0, authoritative_read ? 1 : 0,
        initial_slot_isolation ? 1 : 0, two_slot_mapping ? 1 : 0,
        complete_button_surface ? 1 : 0, action_drives_tilt ? 1 : 0,
        independent_angle_clamping ? 1 : 0,
        inactive_actions_are_neutral ? 1 : 0, generic_full_fallback ? 1 : 0,
        action_recovery ? 1 : 0, native_vibration_routed ? 1 : 0,
        vibration_deduplicated ? 1 : 0,
        native_light_routed ? 1 : 0, fallback_before_native_outputs ? 1 : 0,
        original_vibration_fallback ? 1 : 0, fallback_did_not_route_vibration ? 1 : 0,
        original_light_fallback ? 1 : 0, disconnect_fallback ? 1 : 0, reconnect ? 1 : 0,
        blocked_worker_does_not_block_read ? 1 : 0,
        static_cast<unsigned long long>(stale_elapsed),
        blocked_worker_does_not_block_output ? 1 : 0,
        static_cast<unsigned long long>(blocked_output_elapsed),
        worker_recovery ? 1 : 0, exact_index_priority ? 1 : 0,
        close_cancels_stale_output ? 1 : 0, no_raw_motion ? 1 : 0,
        steam.controller_calls(), close_ok ? 1 : 0, passed ? 1 : 0);
    record_stage(summary);

    steam_shutdown();
    return passed ? 0 : 7;
}
