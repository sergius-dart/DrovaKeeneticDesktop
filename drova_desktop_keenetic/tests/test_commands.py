from drova_desktop_keenetic.common.commands import WmicGetLocalDrives


def test_WmicGetLocalDrives():
    parseNoneDrives = WmicGetLocalDrives.parse("""Name""")
    assert len(parseNoneDrives) == 0

    parseOnlyC = WmicGetLocalDrives.parse(
        """Name
C:\\"""
    )
    assert len(parseOnlyC) == 1
    assert parseOnlyC[0] == "C"

    parseCX = WmicGetLocalDrives.parse(
        """Name
C:\\
X:\\"""
    )
    assert len(parseCX) == 2
    assert parseCX[0] == "C"
    assert parseCX[1] == "X"
