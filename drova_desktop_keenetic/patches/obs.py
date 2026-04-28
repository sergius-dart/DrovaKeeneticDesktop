import asyncio
import io
import json
import logging
from configparser import ConfigParser
from pathlib import PureWindowsPath

from mslex import quote

from drova_desktop_keenetic.common.commands import ObsStartStreaming
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
        appdata = PureWindowsPath(r"C:\ProgramData")
        profile_path = appdata / "obs-studio" / "basic" / "profiles" / profile_name
        await self._create_remote_dirs(ctx, profile_path)

        # ===== 1. Создаём profile.ini через ConfigParser =====
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

        async with ctx.sftp.open(profile_path / "profile.ini", "w") as f:
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

        # ===== 3. Создаём базовую сцену (опционально) =====
        # Проверяем, существует ли файл scenes.json, если нет — создаём
        scenes_path = appdata / "obs-studio" / "basic" / "scenes.json"

        try:
            # Пробуем прочитать существующий scenes.json
            async with ctx.sftp.open(scenes_path, "r") as f:
                scenes_content = await f.read()
                scenes = json.loads(scenes_content)
        except Exception:  # pylint: disable=W0718
            # Создаём новую сцену
            scenes = {
                "current_scene": "Desktop Capture",
                "scenes": [
                    {
                        "name": "Desktop Capture",
                        "sources": [
                            {
                                "enabled": True,
                                "id": "monitor_capture",
                                "name": "Display Capture",
                                "settings": {"capture_cursor": True, "method": "DXGI", "monitor": "0"},
                                "type": "display_capture",
                                "versioned_id": "monitor_capture",
                            }
                        ],
                    }
                ],
                "sources": [],
                "groups": [],
                "modules": {},
            }

            async with ctx.sftp.open(scenes_path, "w") as f:
                await f.write(json.dumps(scenes, indent=2))

        logger.info(f"[ObsRecordDesktop] Profile '{profile_name}' created with ConfigParser")
        logger.debug(f"[ObsRecordDesktop] RTMP server: {self.rtmp_server}, stream key: {self.stream_key}")

    async def _start_obs(self, ctx: SessionHandlerContext, profile: str):
        assert ctx.ssh
        assert ctx.sftp

        cmd = ObsStartStreaming(profile=profile)

        result = await ctx.ssh.run(f"start /d {quote(str(cmd.OBS_PATH.parent))} " + str(cmd), check=False)

        if result.exit_status != 0:
            logger.error(f"[ObsRecordDesktop] Failed to start OBS: {to_str(result.stderr)}")
            raise RuntimeError(f"OBS failed to start: {to_str(result.stderr)}")

        await asyncio.sleep(3)

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
