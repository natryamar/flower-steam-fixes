#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <cstring>

namespace {

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

SRWLOCK g_lock = SRWLOCK_INIT;
volatile LONG g_read_count = 0;
volatile LONG g_vibration_count = 0;
volatile LONG g_light_bar_count = 0;
ScePadVibrationParam g_last_vibration{};
ScePadLightBarParam g_last_light_bar{};

void fill_original_state(ScePadData* data) {
    if (data == nullptr) {
        return;
    }
    std::memset(data, 0, sizeof(*data));
    data->buttons = UINT32_C(0x00ABCDEF);
    data->left_stick_x = 11;
    data->left_stick_y = 22;
    data->right_stick_x = 33;
    data->right_stick_y = 44;
    data->left_trigger = 55;
    data->right_trigger = 66;
    data->orientation[0] = 1.0F;
    data->orientation[1] = 2.0F;
    data->orientation[2] = 3.0F;
    data->orientation[3] = 4.0F;
    data->acceleration[0] = 5.0F;
    data->acceleration[1] = 6.0F;
    data->acceleration[2] = 7.0F;
    data->angular_velocity[0] = 8.0F;
    data->angular_velocity[1] = 9.0F;
    data->angular_velocity[2] = 10.0F;
    std::memset(data->touch_data, 0x11, sizeof(data->touch_data));
    data->connected = 0;
    data->timestamp = UINT64_C(0x1122334455667788);
    std::memset(data->extension_data, 0x22, sizeof(data->extension_data));
    data->connected_count = 0;
    std::memset(data->reserved, 0x33, sizeof(data->reserved));
}

} // namespace

extern "C" __declspec(dllexport) void FlowerFakeScePadReset() {
    (void)InterlockedExchange(&g_read_count, 0);
    (void)InterlockedExchange(&g_vibration_count, 0);
    (void)InterlockedExchange(&g_light_bar_count, 0);
    AcquireSRWLockExclusive(&g_lock);
    g_last_vibration = {};
    g_last_light_bar = {};
    ReleaseSRWLockExclusive(&g_lock);
}

extern "C" __declspec(dllexport) LONG FlowerFakeScePadGetReadCount() {
    return InterlockedCompareExchange(&g_read_count, 0, 0);
}

extern "C" __declspec(dllexport) LONG FlowerFakeScePadGetVibrationCount() {
    return InterlockedCompareExchange(&g_vibration_count, 0, 0);
}

extern "C" __declspec(dllexport) LONG FlowerFakeScePadGetLightBarCount() {
    return InterlockedCompareExchange(&g_light_bar_count, 0, 0);
}

extern "C" __declspec(dllexport) std::uint16_t FlowerFakeScePadGetLastVibration() {
    AcquireSRWLockShared(&g_lock);
    const std::uint16_t value =
        static_cast<std::uint16_t>(g_last_vibration.large_motor) |
        (static_cast<std::uint16_t>(g_last_vibration.small_motor) << 8U);
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" __declspec(dllexport) std::uint32_t FlowerFakeScePadGetLastLightBar() {
    AcquireSRWLockShared(&g_lock);
    const std::uint32_t value =
        (static_cast<std::uint32_t>(g_last_light_bar.red) << 16U) |
        (static_cast<std::uint32_t>(g_last_light_bar.green) << 8U) |
        static_cast<std::uint32_t>(g_last_light_bar.blue);
    ReleaseSRWLockShared(&g_lock);
    return value;
}

extern "C" std::int32_t scePadInit() { return 0; }

extern "C" std::int32_t scePadOpen(std::int32_t user_id, std::int32_t, std::int32_t,
                                   const void*) {
    return user_id > 0 ? user_id * 257 : -1;
}

extern "C" std::int32_t scePadClose(std::int32_t) { return 0; }

extern "C" std::int32_t scePadReadState(std::int32_t, ScePadData* data) {
    (void)InterlockedIncrement(&g_read_count);
    fill_original_state(data);
    return 0;
}

extern "C" std::int32_t scePadSetVibration(std::int32_t,
                                           const ScePadVibrationParam* vibration) {
    if (vibration != nullptr) {
        AcquireSRWLockExclusive(&g_lock);
        g_last_vibration = *vibration;
        ReleaseSRWLockExclusive(&g_lock);
    }
    (void)InterlockedIncrement(&g_vibration_count);
    return 0;
}

extern "C" std::int32_t scePadSetLightBar(std::int32_t,
                                          const ScePadLightBarParam* light_bar) {
    if (light_bar != nullptr) {
        AcquireSRWLockExclusive(&g_lock);
        g_last_light_bar = *light_bar;
        ReleaseSRWLockExclusive(&g_lock);
    }
    (void)InterlockedIncrement(&g_light_bar_count);
    return 0;
}

extern "C" std::int32_t scePadGetControllerInformation() { return 0; }
extern "C" std::int32_t scePadGetHandle() { return 0; }
extern "C" std::int32_t scePadGetJackState() { return 0; }
extern "C" std::int32_t scePadGetParticularMode() { return 0; }
extern "C" std::int32_t scePadIsSupportedAudioFunction() { return 0; }
extern "C" std::int32_t scePadRead() { return 0; }
extern "C" std::int32_t scePadResetLightBar() { return 0; }
extern "C" std::int32_t scePadResetOrientation() { return 0; }
extern "C" std::int32_t scePadSetAngularVelocityDeadbandState() { return 0; }
extern "C" std::int32_t scePadSetAudioOutPath() { return 0; }
extern "C" std::int32_t scePadSetMotionSensorState() { return 0; }
extern "C" std::int32_t scePadSetParticularMode() { return 0; }
extern "C" std::int32_t scePadSetTiltCorrectionState() { return 0; }
extern "C" std::int32_t scePadSetVolumeGain() { return 0; }
