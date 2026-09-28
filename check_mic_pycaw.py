import comtypes
from pycaw.constants import EDataFlow
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def check_microphones():
    print("Enumerating recording devices...")
    device_enumerator = AudioUtilities.GetDeviceEnumerator()
    collection = device_enumerator.EnumAudioEndpoints(
        EDataFlow.eCapture.value, 1  # DEVICE_STATE_ACTIVE
    )
    count = collection.GetCount()
    print(f"Active Capture Devices Count: {count}")

    for i in range(count):
        dev = collection.Item(i)
        interface = dev.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)

        is_muted = volume.GetMute()
        level = volume.GetMasterVolumeLevelScalar()
        print(f"\n[Device {i}] ID: {dev.GetId()}")
        print(f"  Muted: {is_muted}")
        print(f"  Volume Level: {level * 100:.1f}%")

        if is_muted:
            print("  --> UNMUTING DEVICE!")
            volume.SetMute(0, None)
        if level < 0.5:
            print("  --> BOOSTING VOLUME TO 100%!")
            volume.SetMasterVolumeLevelScalar(1.0, None)

        print(f"  New Muted State: {volume.GetMute()}")
        print(f"  New Volume: {volume.GetMasterVolumeLevelScalar() * 100:.1f}%")


if __name__ == "__main__":
    check_microphones()
