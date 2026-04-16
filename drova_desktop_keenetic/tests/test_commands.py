from drova_desktop_keenetic.common.commands import WmicGetLocalDrives


def test_WmicGetLocalDrives():  # pylint: disable=C0103
    parse_none_drives = WmicGetLocalDrives.parse("""Name""")
    assert len(parse_none_drives) == 0

    parse_only_c = WmicGetLocalDrives.parse(
        """Name
C:\\"""
    )
    assert len(parse_only_c) == 1
    assert parse_only_c[0] == "C"

    parse_cx = WmicGetLocalDrives.parse(
        """Name
C:\\
X:\\"""
    )
    assert len(parse_cx) == 2
    assert parse_cx[0] == "C"
    assert parse_cx[1] == "X"
