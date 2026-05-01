import asyncio
import io
import json
import logging
from configparser import ConfigParser
from pathlib import PureWindowsPath

from drova_desktop_keenetic.common.commands import ObsStartStreaming, PsExec
from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.helpers import to_str
from drova_desktop_keenetic.common.patch import (
    ISessionHandler,
    SessionHandlerContext,
    patcher,
)

logger = logging.getLogger(__name__)


@patcher
class ObsRecordDesktop(ISessionHandler):
    PRIORITY = 100
    TASKKILL_IMAGE = "obs64.exe"

    def __init__(self, config: Config):
        super().__init__(config)
        self.rtmp_server = config.obs_remote_url
        self.stream_key = config.windows_host
        self.obs_pid: str | None = None

    @property
    def rtmp_url(self):
        return f"{self.rtmp_server}/{self.stream_key}"

    async def on_idle(self, ctx: SessionHandlerContext):
        return

    async def on_session_start(self, ctx: SessionHandlerContext):
        assert ctx.ssh
        assert ctx.sftp
        assert ctx.session

        if not self.rtmp_server:
            return

        try:
            # Full RTMP URL

            # Создаём временный профиль OBS на Windows
            profile_name = f"session_{ctx.session.uuid}"
            await self._create_obs_profile(ctx, profile_name)

            # Запускаем OBS с нужным профилем
            await self._start_obs(ctx, profile_name)

            logger.info(f"[ObsRecordDesktop] OBS started, streaming to {self.rtmp_url}")

        except Exception as e:  # pylint: disable=W0718
            logger.exception(f"[ObsRecordDesktop] Error starting session: {e}")

    async def on_session_active(self, ctx: SessionHandlerContext):
        return

    async def on_session_end(self, ctx: SessionHandlerContext):
        if not self.rtmp_server:
            return

        assert ctx.ssh
        try:
            if self.obs_pid:
                logger.info(f"[ObsRecordDesktop] Stopping OBS process {self.obs_pid}")

                await ctx.ssh.run(f"taskkill /PID {self.obs_pid}", check=False)
                await asyncio.sleep(2)

                # check finished process
                check_cmd = f'tasklist /FI "PID eq {self.obs_pid}" /NH'
                result = await ctx.ssh.run(check_cmd, check=False)

                if "obs64.exe" in to_str(result.stdout):
                    logger.warning(f"[ObsRecordDesktop] Process {self.obs_pid} still running, forcing...")
                    await ctx.ssh.run(f"taskkill /F /PID {self.obs_pid}", check=False)
            else:
                # if not pid - close force by name
                logger.info("[ObsRecordDesktop] No PID, closing by image name")
                await ctx.ssh.run(f"taskkill /F /IM {self.TASKKILL_IMAGE}", check=False)

            # 3. Даём время на сохранение файлов
            await asyncio.sleep(2)

            logger.info("[ObsRecordDesktop] OBS stopped successfully")

        except Exception as e:  # pylint: disable=W0718
            logger.exception(f"[ObsRecordDesktop] Error stopping OBS: {e}")
        finally:
            self.obs_pid = None

    async def _create_obs_profile(self, ctx: SessionHandlerContext, profile_name: str):
        assert ctx.ssh
        assert ctx.sftp
        assert ctx.session

        app_name = "live"

        # Путь к профилю на Windows
        appdata = PureWindowsPath(r"AppData\Roaming")
        profile_path = appdata / "obs-studio" / "basic" / "profiles" / profile_name
        await self._create_remote_dirs(ctx, profile_path)

        # ===== 1. Создаём basic.ini через ConfigParser =====
        profile_ini = ConfigParser()

        # Секция [General]
        profile_ini["General"] = {"Name": profile_name}

        # Секция [Video]
        profile_ini["Video"] = {
            "BaseCX": "1920",
            "BaseCY": "1080",
            "OutputCX": "1280",
            "OutputCY": "720",
            "FPSType": "Common",
            "FPSCommon": "30",
            "ScaleType": "bicubic",
        }

        # Секция [Audio]
        profile_ini["Audio"] = {"SampleRate": "48000", "Channels": "2"}

        # Секция [AdvOut] (Advanced Output Settings)
        profile_ini["AdvOut"] = {
            "ApplyServiceSettings": "true",
            "UseRescale": "false",
            "VEncoder": "obs_x264",
            "VBitrate": "2500",
            "VKeyframeInterval": "2",
            "VUseCustomSettings": "false",
            "AEncoder": "ffmpeg_aac",
            "ABitrate": "160",
            "AudioTrack": "1",
            "Track1Bitrate": "160",
            "TrackName": "track1",
        }

        # Секция [Publish]
        profile_ini["Publish"] = {"BindIP": "default"}

        async with ctx.sftp.open(profile_path / "basic.ini", "w") as f:
            config_buffer = io.StringIO()
            profile_ini.write(config_buffer)
            config_buffer.seek(0)

            profile_ini_content = config_buffer.getvalue()
            await f.write(profile_ini_content)

        # ===== 2. Создаём service.json (настройки стрима) =====
        service_config = {
            "settings": {
                "server": self.rtmp_server,
                "key": self.stream_key,
                "service": app_name,
                "use_auth": False,
                "enable_bw_test": False,
            },
            "type": "rtmp_custom",
            "name": "default_service",
        }

        async with ctx.sftp.open(profile_path / "service.json", "w") as f:
            await f.write(json.dumps(service_config, indent=2))

        monitor_device_path = await self._wait_drova_monitor(ctx)

        # ===== 3. Создаём базовую сцену (опционально) =====
        # Проверяем, существует ли файл scenes.json, если нет — создаём
        scenes_path = appdata / "obs-studio" / "basic" / "scenes" / "scenes.json"

        # Создаём новую сцену
        scenes = {
            "name": "scene",
            "DesktopAudioDevice1": {
                "name": "Main Sound ",
                "uuid": "8e6a99d8-01b6-4384-b140-188d0fb98170",
                "id": "wasapi_output_capture",
                "versioned_id": "wasapi_output_capture",
                "settings": {"device_id": "default"},
                "mixers": 255,
                "sync": 0,
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "enabled": True,
                "muted": False,
                "push-to-mute": False,
                "push-to-mute-delay": 0,
                "push-to-talk": False,
                "push-to-talk-delay": 0,
                "deinterlace_mode": 0,
                "deinterlace_field_order": 0,
                "monitoring_type": 0,
                "private_settings": {},
            },
            "sources": [
                {
                    "prev_ver": 536936450,
                    "name": "2",
                    "uuid": "f87dbbe6-fa7c-4cca-9b3b-0614a0505873",
                    "id": "monitor_capture",
                    "versioned_id": "monitor_capture",
                    "settings": {"monitor_id": monitor_device_path, "method": 1},
                    "mixers": 0,
                    "sync": 0,
                    "flags": 0,
                    "volume": 1.0,
                    "balance": 0.5,
                    "enabled": True,
                    "muted": False,
                    "push-to-mute": False,
                    "push-to-mute-delay": 0,
                    "push-to-talk": False,
                    "push-to-talk-delay": 0,
                    "hotkeys": {},
                    "deinterlace_mode": 0,
                    "deinterlace_field_order": 0,
                    "monitoring_type": 0,
                    "private_settings": {},
                },
                {
                    "prev_ver": 536936450,
                    "name": "1",
                    "uuid": "df6040a5-e98a-4e54-90df-94b64794c209",
                    "id": "scene",
                    "versioned_id": "scene",
                    "settings": {
                        "id_counter": 2,
                        "custom_size": False,
                        "items": [
                            {
                                "name": "2",
                                "source_uuid": "f87dbbe6-fa7c-4cca-9b3b-0614a0505873",
                                "visible": True,
                                "locked": False,
                                "rot": 0.0,
                                "align": 5,
                                "bounds_type": 0,
                                "bounds_align": 0,
                                "bounds_crop": False,
                                "crop_left": 0,
                                "crop_top": 0,
                                "crop_right": 0,
                                "crop_bottom": 0,
                                "id": 2,
                                "group_item_backup": False,
                                "pos": {"x": 0.0, "y": 0.0},
                                "scale": {"x": 1.0, "y": 1.0},
                                "bounds": {"x": 0.0, "y": 0.0},
                                "scale_filter": "disable",
                                "blend_method": "default",
                                "blend_type": "normal",
                                "show_transition": {"duration": 300},
                                "hide_transition": {"duration": 300},
                                "private_settings": {},
                            }
                        ],
                    },
                    "mixers": 0,
                    "sync": 0,
                    "flags": 0,
                    "volume": 1.0,
                    "balance": 0.5,
                    "enabled": True,
                    "muted": False,
                    "push-to-mute": False,
                    "push-to-mute-delay": 0,
                    "push-to-talk": False,
                    "push-to-talk-delay": 0,
                    "hotkeys": {
                        "OBSBasic.SelectScene": [],
                        "libobs.show_scene_item.2": [],
                        "libobs.hide_scene_item.2": [],
                    },
                    "deinterlace_mode": 0,
                    "deinterlace_field_order": 0,
                    "monitoring_type": 0,
                    "canvas_uuid": "6c69626f-6273-4c00-9d88-c5136d61696e",
                    "private_settings": {},
                },
            ],
            "modules": {
                "scripts-tool": [],
                "output-timer": {
                    "streamTimerHours": 0,
                    "streamTimerMinutes": 0,
                    "streamTimerSeconds": 0,
                    "recordTimerHours": 0,
                    "recordTimerMinutes": 0,
                    "recordTimerSeconds": 0,
                    "autoStartStreamTimer": False,
                    "autoStartRecordTimer": False,
                    "pauseRecordTimer": False,
                },
                "auto-scene-switcher": {
                    "interval": 300,
                    "non_matching_scene": "",
                    "switch_if_not_matching": False,
                    "active": False,
                    "switches": [],
                },
                "captions": {"source": "", "enabled": False, "lang_id": 1049, "provider": "mssapi"},
            },
            "resolution": {"x": 1920, "y": 1080},
            "version": 1,
        }

        async with ctx.sftp.open(scenes_path, "w") as f:
            await f.write(json.dumps(scenes, indent=2))

        logger.info(f"[ObsRecordDesktop] Profile '{profile_name}' created with ConfigParser")
        logger.debug(f"[ObsRecordDesktop] RTMP server: {self.rtmp_server}, stream key: {self.stream_key}")

    async def _wait_drova_monitor(self, ctx: SessionHandlerContext):
        assert ctx.ssh
        for _ in range(30):  # wait 30 seconds
            try:
                # Запрос всех подключенных мониторов из реестра
                reg_cmd = "wmic desktopmonitor get pnpdeviceid"
                result = await ctx.ssh.run(reg_cmd, check=False)

                if result.exit_status == 0 and result.stdout:
                    output = to_str(result.stdout)
                    # Ищем строки с Device Path формата \\?\DISPLAY#
                    for line in output.split("\n"):
                        line = line.strip()
                        if "DRO00DD" in line:  # use only DROVA monitor
                            return "\\\\?\\" + line.replace("\\", "#") + "#{e6f07b5f-ee97-4a90-b076-33f57bf4eaa7}"
            except Exception as e:  # pylint: disable=W0718
                logger.warning(f"[ObsRecordDesktop] Failed to query registry for monitor: {e}")

            await asyncio.sleep(1)  # wait monitor create
        return "\\\\?\\DISPLAY#DRO00DD#1&28a6823a&0&UID256#{e6f07b5f-ee97-4a90-b076-33f57bf4eaa7}"

    async def _start_obs(self, ctx: SessionHandlerContext, profile: str):
        assert ctx.ssh
        assert ctx.sftp

        cmd = PsExec(
            command=ObsStartStreaming(profile=profile, collection="scene", scene="scene"),
            working_directory=ObsStartStreaming.OBS_PATH.parent,
        )

        await ctx.ssh.run(str(cmd), check=False)

        await asyncio.sleep(1)

        pid_cmd = 'for /f "tokens=2" %a in (\'tasklist /fi "imagename eq obs64.exe" /nh\') do @echo %a'

        pid_result = await ctx.ssh.run(pid_cmd, check=False)
        self.obs_pid = to_str(pid_result.stdout).strip()

        if self.obs_pid:
            logger.info(f"[ObsRecordDesktop] OBS PID: {self.obs_pid}")
        else:
            self.obs_pid = None
            logger.warning("[ObsRecordDesktop] Could not get OBS PID")

    async def _create_remote_dirs(self, ctx: SessionHandlerContext, path: PureWindowsPath):
        assert ctx.sftp
        parts = path.parts
        current = PureWindowsPath(parts[0])  # "C:"

        for part in parts[1:]:
            current = current / part

            try:
                await ctx.sftp.mkdir(current)
                logger.debug(f"[ObsRecordDesktop] Created directory: {current}")
            except Exception:  # pylint: disable=W0718
                logger.debug(f"[ObsRecordDesktop] Directory exists: {current}")
