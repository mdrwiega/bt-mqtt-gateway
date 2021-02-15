from interruptingcow import timeout

import logger
from exceptions import DeviceTimeoutError
from mqtt import MqttMessage
from workers.base import BaseWorker

_LOGGER = logger.get(__name__)

REQUIREMENTS = [
    "git+https://github.com/zewelor/linak_bt_desk.git@aa9412f98b3044be34c70e89d02721e6813ea731#egg=linakdpgbt"
]


class LinakdeskWorker(BaseWorker):

    SCAN_TIMEOUT = 20

    def _setup(self):
        from linak_dpg_bt import LinakDesk

        self.desk = LinakDesk(self.mac)

        _LOGGER.info("Created LinakDesk worker")

    def status_update(self):
        return [
            MqttMessage(
                topic=self.format_topic("height/cm"), payload=self._get_height()
            )
        ]

    def _get_height(self):
        from bluepy import btle

        with timeout(
            self.SCAN_TIMEOUT,
            exception=DeviceTimeoutError(
                "Retrieving the height from {} device {} timed out after {} seconds".format(
                    repr(self), self.mac, self.SCAN_TIMEOUT
                )
            ),
        ):
            try:
                self.desk.read_dpg_data()
                return self.desk.current_height_with_offset.cm + self.desk_offset_cm
            except btle.BTLEException as e:
                logger.log_exception(
                    _LOGGER,
                    "Error during update of linak desk '%s' (%s): %s",
                    repr(self),
                    self.mac,
                    type(e).__name__,
                    suppress=True,
                )
                raise DeviceTimeoutError

    def on_command(self, topic, value):
        target_height = float(value)

        if target_height >= self.min_height_cm and target_height <= self.max_height_cm:
            _LOGGER.info("Start moving desk to the target height: %.1f", target_height)
            self.desk.move_to_cm(target_height - self.desk_offset_cm)