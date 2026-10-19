// GNOME's screenshot notifications come from the shell's own "Screen Capture" source, which
// has no switch in Settings > Notifications. Drop them before they reach the message tray.
// Screen recordings use the same source, so their notifications go too.
import Gio from 'gi://Gio';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const SCREEN_CAPTURE_ICON = 'screenshooter-symbolic';

function isScreenCaptureSource(source) {
    return source.icon instanceof Gio.ThemedIcon &&
        source.icon.get_names().includes(SCREEN_CAPTURE_ICON);
}

export default class QuietScreenshots extends Extension {
    enable() {
        this._injections = new InjectionManager();
        this._injections.overrideMethod(MessageTray.Source.prototype, 'addNotification',
            addNotification => function (notification) {
                if (isScreenCaptureSource(this))
                    return;
                addNotification.call(this, notification);
            });
    }

    disable() {
        this._injections.clear();
        this._injections = null;
    }
}
