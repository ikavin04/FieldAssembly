"""Utility to inspect and unmute Windows recording devices."""
import comtypes
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from pycaw.constants import EDataFlow


def get_mic_status():
    """Check default audio capture device status."""
    device_enumerator = AudioUtilities.GetDeviceEnumerator()
    collection = device_enumerator.EnumAudioEndpoints(
        EDataFlow.eCapture.value, 1
    )
    count = collection.GetCount()
    print(f"Active Capture Devices: {count}")

    for i in range(count):
        dev = collection.Item(i)
        interface = dev.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)

        is_muted = volume.GetMute()
        level = volume.GetMasterVolumeLevelScalar()
        print(f"Device [{i}]: Muted={bool(is_muted)}, Volume={level * 100:.1f}%")

        if is_muted:
            print("Unmuting device...")
            volume.SetMute(0, None)
        if level < 0.5:
            print("Boosting volume to 100%...")
            volume.SetMasterVolumeLevelScalar(1.0, None)


if __name__ == "__main__":
    get_mic_status()
