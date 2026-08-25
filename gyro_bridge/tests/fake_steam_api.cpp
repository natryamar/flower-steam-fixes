#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <cstring>

namespace {

constexpr int kControllerCount = 2;
constexpr std::uint64_t kControllerHandles[kControllerCount] = {42, 84};
constexpr std::uint64_t kActionSetHandle = 1;
constexpr std::uint64_t kLeftStickHandle = 2;
constexpr std::uint64_t kRightStickHandle = 3;
constexpr std::uint64_t kTiltHandle = 4;
constexpr std::uint64_t kDpadUpHandle = 10;
constexpr std::uint64_t kDpadRightHandle = 11;
constexpr std::uint64_t kDpadDownHandle = 12;
constexpr std::uint64_t kDpadLeftHandle = 13;
constexpr std::uint64_t kSquareHandle = 14;
constexpr std::uint64_t kCrossHandle = 15;
constexpr std::uint64_t kCircleHandle = 16;
constexpr std::uint64_t kTriangleHandle = 17;
constexpr std::uint64_t kL1Handle = 18;
constexpr std::uint64_t kR1Handle = 19;
constexpr std::uint64_t kL2Handle = 20;
constexpr std::uint64_t kR2Handle = 21;
constexpr std::uint64_t kOptionsHandle = 22;
constexpr std::uint64_t kTouchpadClickHandle = 23;

constexpr std::uint32_t kButtonOptions = UINT32_C(0x00000008);
constexpr std::uint32_t kButtonDpadUp = UINT32_C(0x00000010);
constexpr std::uint32_t kButtonDpadRight = UINT32_C(0x00000020);
constexpr std::uint32_t kButtonDpadDown = UINT32_C(0x00000040);
constexpr std::uint32_t kButtonDpadLeft = UINT32_C(0x00000080);
constexpr std::uint32_t kButtonL2 = UINT32_C(0x00000100);
constexpr std::uint32_t kButtonR2 = UINT32_C(0x00000200);
constexpr std::uint32_t kButtonL1 = UINT32_C(0x00000400);
constexpr std::uint32_t kButtonR1 = UINT32_C(0x00000800);
constexpr std::uint32_t kButtonTriangle = UINT32_C(0x00001000);
constexpr std::uint32_t kButtonCircle = UINT32_C(0x00002000);
constexpr std::uint32_t kButtonCross = UINT32_C(0x00004000);
constexpr std::uint32_t kButtonSquare = UINT32_C(0x00008000);
constexpr std::uint32_t kButtonTouchpadClick = UINT32_C(0x00100000);

struct ControllerMotionData {
    float quaternion_x;
    float quaternion_y;
    float quaternion_z;
    float quaternion_w;
    float acceleration_x;
    float acceleration_y;
    float acceleration_z;
    float angular_velocity_x;
    float angular_velocity_y;
    float angular_velocity_z;
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

struct FakeControllerState {
    float left_stick_x;
    float left_stick_y;
    float right_stick_x;
    float right_stick_y;
    float tilt_x;
    float tilt_y;
    std::uint32_t buttons;
    bool surface_active;
    bool tilt_active;
};

static_assert(sizeof(ControllerMotionData) == 40);
static_assert(sizeof(ControllerDigitalActionData) == 2);
static_assert(sizeof(ControllerAnalogActionData) == 16);

int g_interface_marker = 0;
int g_controller_marker = 0;
SRWLOCK g_lock = SRWLOCK_INIT;
FakeControllerState g_states[kControllerCount]{};
int g_connected_count = 1;
int g_enumeration_order[kControllerCount] = {0, 1};
int g_gamepad_indices[kControllerCount] = {0, 1};
DWORD g_run_frame_delay = 0;
DWORD g_vibration_delay = 0;
volatile LONG g_controller_call_count = 0;
volatile LONG g_run_frame_count = 0;
volatile LONG g_motion_call_count = 0;
volatile LONG g_vibration_entry_count = 0;
volatile LONG g_vibration_call_count = 0;
volatile LONG g_led_call_count = 0;
std::uint64_t g_last_output_handle = 0;
std::uint16_t g_last_vibration_left = 0;
std::uint16_t g_last_vibration_right = 0;
std::uint8_t g_last_led_red = 0;
std::uint8_t g_last_led_green = 0;
std::uint8_t g_last_led_blue = 0;

LONG read_counter(volatile LONG* counter) {
    return InterlockedCompareExchange(counter, 0, 0);
}

void count_controller_call() { (void)InterlockedIncrement(&g_controller_call_count); }

int controller_index(std::uint64_t handle) {
    for (int index = 0; index < kControllerCount; ++index) {
        if (kControllerHandles[index] == handle) {
            return index;
        }
    }
    return -1;
}

bool valid_index(int index) { return index >= 0 && index < kControllerCount; }

bool controller_is_connected_locked(int controller_index_value) {
    for (int index = 0; index < g_connected_count; ++index) {
        if (g_enumeration_order[index] == controller_index_value) {
            return true;
        }
    }
    return false;
}

void reset_state_locked() {
    g_states[0] = {
        0.5F, -0.25F, -0.75F, 0.75F, 0.0F, 0.0F, kButtonCross | kButtonOptions,
        true, true};
    g_states[1] = {
        -0.5F, 0.25F, 0.25F, -0.5F, 0.0F, 0.0F, kButtonCircle | kButtonTouchpadClick,
        true,  true};
    g_connected_count = 1;
    g_enumeration_order[0] = 0;
    g_enumeration_order[1] = 1;
    g_gamepad_indices[0] = 0;
    g_gamepad_indices[1] = 1;
    g_run_frame_delay = 0;
    g_vibration_delay = 0;
    g_last_output_handle = 0;
    g_last_vibration_left = 0;
    g_last_vibration_right = 0;
    g_last_led_red = 0;
    g_last_led_green = 0;
    g_last_led_blue = 0;
}

std::uint64_t digital_handle_for_name(const char* name) {
    if (std::strcmp(name, "dpad_up") == 0) {
        return kDpadUpHandle;
    }
    if (std::strcmp(name, "dpad_right") == 0) {
        return kDpadRightHandle;
    }
    if (std::strcmp(name, "dpad_down") == 0) {
        return kDpadDownHandle;
    }
    if (std::strcmp(name, "dpad_left") == 0) {
        return kDpadLeftHandle;
    }
    if (std::strcmp(name, "square") == 0) {
        return kSquareHandle;
    }
    if (std::strcmp(name, "cross") == 0) {
        return kCrossHandle;
    }
    if (std::strcmp(name, "circle") == 0) {
        return kCircleHandle;
    }
    if (std::strcmp(name, "triangle") == 0) {
        return kTriangleHandle;
    }
    if (std::strcmp(name, "l1") == 0) {
        return kL1Handle;
    }
    if (std::strcmp(name, "r1") == 0) {
        return kR1Handle;
    }
    if (std::strcmp(name, "l2") == 0) {
        return kL2Handle;
    }
    if (std::strcmp(name, "r2") == 0) {
        return kR2Handle;
    }
    if (std::strcmp(name, "options") == 0) {
        return kOptionsHandle;
    }
    if (std::strcmp(name, "touchpad_click") == 0) {
        return kTouchpadClickHandle;
    }
    return 0;
}

std::uint32_t button_mask_for_handle(std::uint64_t handle) {
    switch (handle) {
    case kDpadUpHandle:
        return kButtonDpadUp;
    case kDpadRightHandle:
        return kButtonDpadRight;
    case kDpadDownHandle:
        return kButtonDpadDown;
    case kDpadLeftHandle:
        return kButtonDpadLeft;
    case kSquareHandle:
        return kButtonSquare;
    case kCrossHandle:
        return kButtonCross;
    case kCircleHandle:
        return kButtonCircle;
    case kTriangleHandle:
        return kButtonTriangle;
    case kL1Handle:
        return kButtonL1;
    case kR1Handle:
        return kButtonR1;
    case kL2Handle:
        return kButtonL2;
    case kR2Handle:
        return kButtonR2;
    case kOptionsHandle:
        return kButtonOptions;
    case kTouchpadClickHandle:
        return kButtonTouchpadClick;
    default:
        return 0;
    }
}

} // namespace

extern "C" __declspec(dllexport) void FlowerFakeSteamReset() {
    AcquireSRWLockExclusive(&g_lock);
    reset_state_locked();
    ReleaseSRWLockExclusive(&g_lock);
    (void)InterlockedExchange(&g_controller_call_count, 0);
    (void)InterlockedExchange(&g_run_frame_count, 0);
    (void)InterlockedExchange(&g_motion_call_count, 0);
    (void)InterlockedExchange(&g_vibration_entry_count, 0);
    (void)InterlockedExchange(&g_vibration_call_count, 0);
    (void)InterlockedExchange(&g_led_call_count, 0);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetConnectedCount(int count) {
    AcquireSRWLockExclusive(&g_lock);
    g_connected_count =
        count < 0 ? 0 : (count > kControllerCount ? kControllerCount : count);
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void
FlowerFakeSteamSetEnumerationReversed(BOOL reversed) {
    AcquireSRWLockExclusive(&g_lock);
    g_enumeration_order[0] = reversed != FALSE ? 1 : 0;
    g_enumeration_order[1] = reversed != FALSE ? 0 : 1;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void
FlowerFakeSteamSetGamepadIndex(int controller, int gamepad_index) {
    if (!valid_index(controller)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_gamepad_indices[controller] = gamepad_index;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetRunFrameDelay(DWORD delay) {
    AcquireSRWLockExclusive(&g_lock);
    g_run_frame_delay = delay;
    ReleaseSRWLockExclusive(&g_lock);
}


extern "C" __declspec(dllexport) void FlowerFakeSteamSetVibrationDelay(DWORD delay) {
    AcquireSRWLockExclusive(&g_lock);
    g_vibration_delay = delay;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetSurfaceActive(int index,
                                                                      BOOL active) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].surface_active = active != FALSE;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetTiltActive(int index,
                                                                   BOOL active) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].tilt_active = active != FALSE;
    ReleaseSRWLockExclusive(&g_lock);
}


extern "C" __declspec(dllexport) void
FlowerFakeSteamSetLeftStickValues(int index, float x, float y) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].left_stick_x = x;
    g_states[index].left_stick_y = y;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void
FlowerFakeSteamSetRightStickValues(int index, float x, float y) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].right_stick_x = x;
    g_states[index].right_stick_y = y;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetTiltValues(int index, float x,
                                                                   float y) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].tilt_x = x;
    g_states[index].tilt_y = y;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) void FlowerFakeSteamSetButtons(int index,
                                                                std::uint32_t buttons) {
    if (!valid_index(index)) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_states[index].buttons = buttons;
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetControllerCallCount() {
    return read_counter(&g_controller_call_count);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetRunFrameCount() {
    return read_counter(&g_run_frame_count);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetMotionCallCount() {
    return read_counter(&g_motion_call_count);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetVibrationEntryCount() {
    return read_counter(&g_vibration_entry_count);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetVibrationCallCount() {
    return read_counter(&g_vibration_call_count);
}

extern "C" __declspec(dllexport) LONG FlowerFakeSteamGetLedCallCount() {
    return read_counter(&g_led_call_count);
}

extern "C" __declspec(dllexport) std::uint64_t FlowerFakeSteamGetLastOutputHandle() {
    AcquireSRWLockShared(&g_lock);
    const std::uint64_t value = g_last_output_handle;
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" __declspec(dllexport) std::uint16_t FlowerFakeSteamGetLastVibrationLeft() {
    AcquireSRWLockShared(&g_lock);
    const std::uint16_t value = g_last_vibration_left;
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" __declspec(dllexport) std::uint16_t FlowerFakeSteamGetLastVibrationRight() {
    AcquireSRWLockShared(&g_lock);
    const std::uint16_t value = g_last_vibration_right;
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" __declspec(dllexport) std::uint32_t FlowerFakeSteamGetLastLedRgb() {
    AcquireSRWLockShared(&g_lock);
    const std::uint32_t value = (static_cast<std::uint32_t>(g_last_led_red) << 16U) |
                                (static_cast<std::uint32_t>(g_last_led_green) << 8U) |
                                static_cast<std::uint32_t>(g_last_led_blue);
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" __declspec(dllexport) bool SteamAPI_Init() { return true; }

extern "C" __declspec(dllexport) void SteamAPI_Shutdown() {}

extern "C" __declspec(dllexport) void*
SteamInternal_CreateInterface(const char* version) {
    return version != nullptr && std::strcmp(version, "SteamClient017") == 0
               ? &g_interface_marker
               : nullptr;
}

extern "C" __declspec(dllexport) std::int32_t SteamAPI_GetHSteamUser() { return 1; }

extern "C" __declspec(dllexport) std::int32_t SteamAPI_GetHSteamPipe() { return 1; }

extern "C" __declspec(dllexport) void*
SteamAPI_ISteamClient_GetISteamController(void* client, std::int32_t user,
                                          std::int32_t pipe, const char* version) {
    return client != nullptr && user == 1 && pipe == 1 && version != nullptr &&
                   std::strcmp(version, "SteamController005") == 0
               ? &g_controller_marker
               : nullptr;
}

extern "C" __declspec(dllexport) bool SteamAPI_ISteamController_Init(void* controller) {
    count_controller_call();
    return controller == &g_controller_marker;
}

extern "C" __declspec(dllexport) void
SteamAPI_ISteamController_RunFrame(void* controller) {
    count_controller_call();
    (void)controller;
    (void)InterlockedIncrement(&g_run_frame_count);
    AcquireSRWLockShared(&g_lock);
    const DWORD delay = g_run_frame_delay;
    ReleaseSRWLockShared(&g_lock);
    if (delay > 0) {
        Sleep(delay);
    }
}

extern "C" __declspec(dllexport) int
SteamAPI_ISteamController_GetConnectedControllers(void* controller,
                                                  std::uint64_t* handles) {
    count_controller_call();
    if (controller != &g_controller_marker || handles == nullptr) {
        return 0;
    }
    AcquireSRWLockShared(&g_lock);
    const int count = g_connected_count;
    for (int index = 0; index < count; ++index) {
        handles[index] = kControllerHandles[g_enumeration_order[index]];
    }
    ReleaseSRWLockShared(&g_lock);
    return count;
}

extern "C" __declspec(dllexport) int
SteamAPI_ISteamController_GetGamepadIndexForController(void* controller,
                                                       std::uint64_t handle) {
    count_controller_call();
    if (controller != &g_controller_marker) {
        return -1;
    }
    const int index = controller_index(handle);
    AcquireSRWLockShared(&g_lock);
    const bool connected = valid_index(index) && controller_is_connected_locked(index);
    const int gamepad_index = connected ? g_gamepad_indices[index] : -1;
    ReleaseSRWLockShared(&g_lock);
    return gamepad_index;
}

extern "C" __declspec(dllexport) ControllerMotionData
SteamAPI_ISteamController_GetMotionData(void*, std::uint64_t) {
    count_controller_call();
    (void)InterlockedIncrement(&g_motion_call_count);
    ControllerMotionData data{};
    data.quaternion_w = 1.0F;
    data.acceleration_y = 1.0F;
    return data;
}

extern "C" __declspec(dllexport) std::uint64_t
SteamAPI_ISteamController_GetActionSetHandle(void* controller, const char* name) {
    count_controller_call();
    return controller == &g_controller_marker && name != nullptr &&
                   std::strcmp(name, "flower_ps4") == 0
               ? kActionSetHandle
               : 0;
}

extern "C" __declspec(dllexport) void
SteamAPI_ISteamController_ActivateActionSet(void* controller, std::uint64_t handle,
                                            std::uint64_t action_set) {
    count_controller_call();
    (void)controller;
    (void)handle;
    (void)action_set;
}

extern "C" __declspec(dllexport) std::uint64_t
SteamAPI_ISteamController_GetAnalogActionHandle(void* controller, const char* name) {
    count_controller_call();
    if (controller != &g_controller_marker || name == nullptr) {
        return 0;
    }
    if (std::strcmp(name, "left_stick") == 0) {
        return kLeftStickHandle;
    }
    if (std::strcmp(name, "right_stick") == 0) {
        return kRightStickHandle;
    }
    if (std::strcmp(name, "tilt") == 0) {
        return kTiltHandle;
    }
    return 0;
}

extern "C" __declspec(dllexport) ControllerAnalogActionData
SteamAPI_ISteamController_GetAnalogActionData(void* controller, std::uint64_t handle,
                                              std::uint64_t action) {
    count_controller_call();
    ControllerAnalogActionData data{};
    const int index = controller_index(handle);
    if (controller != &g_controller_marker || !valid_index(index)) {
        return data;
    }

    AcquireSRWLockShared(&g_lock);
    const FakeControllerState state = g_states[index];
    ReleaseSRWLockShared(&g_lock);
    data.mode = 6;
    if (action == kLeftStickHandle) {
        data.x = state.left_stick_x;
        data.y = state.left_stick_y;
        data.active = state.surface_active;
    } else if (action == kRightStickHandle) {
        data.x = state.right_stick_x;
        data.y = state.right_stick_y;
        data.active = state.surface_active;
    } else if (action == kTiltHandle) {
        data.x = state.tilt_x;
        data.y = state.tilt_y;
        data.active = state.tilt_active;
    }
    return data;
}

extern "C" __declspec(dllexport) std::uint64_t
SteamAPI_ISteamController_GetDigitalActionHandle(void* controller, const char* name) {
    count_controller_call();
    if (controller != &g_controller_marker || name == nullptr) {
        return 0;
    }
    return digital_handle_for_name(name);
}

extern "C" __declspec(dllexport) ControllerDigitalActionData
SteamAPI_ISteamController_GetDigitalActionData(void* controller, std::uint64_t handle,
                                               std::uint64_t action) {
    count_controller_call();
    ControllerDigitalActionData data{};
    const int index = controller_index(handle);
    const std::uint32_t button_mask = button_mask_for_handle(action);
    if (controller != &g_controller_marker || !valid_index(index) || button_mask == 0) {
        return data;
    }

    AcquireSRWLockShared(&g_lock);
    const FakeControllerState state = g_states[index];
    ReleaseSRWLockShared(&g_lock);
    data.active = state.surface_active;
    data.state = (state.buttons & button_mask) != 0;
    return data;
}

extern "C" __declspec(dllexport) void
SteamAPI_ISteamController_TriggerVibration(void* controller, std::uint64_t handle,
                                           std::uint16_t left_speed,
                                           std::uint16_t right_speed) {
    count_controller_call();
    if (controller != &g_controller_marker || !valid_index(controller_index(handle))) {
        return;
    }
    (void)InterlockedIncrement(&g_vibration_entry_count);
    AcquireSRWLockShared(&g_lock);
    const DWORD delay = g_vibration_delay;
    ReleaseSRWLockShared(&g_lock);
    if (delay > 0) {
        Sleep(delay);
    }
    AcquireSRWLockExclusive(&g_lock);
    g_last_output_handle = handle;
    g_last_vibration_left = left_speed;
    g_last_vibration_right = right_speed;
    ReleaseSRWLockExclusive(&g_lock);
    (void)InterlockedIncrement(&g_vibration_call_count);
}

extern "C" __declspec(dllexport) void
SteamAPI_ISteamController_SetLEDColor(void* controller, std::uint64_t handle,
                                      std::uint8_t red, std::uint8_t green,
                                      std::uint8_t blue, std::uint32_t flags) {
    count_controller_call();
    (void)flags;
    if (controller != &g_controller_marker || !valid_index(controller_index(handle))) {
        return;
    }
    AcquireSRWLockExclusive(&g_lock);
    g_last_output_handle = handle;
    g_last_led_red = red;
    g_last_led_green = green;
    g_last_led_blue = blue;
    ReleaseSRWLockExclusive(&g_lock);
    (void)InterlockedIncrement(&g_led_call_count);
}
