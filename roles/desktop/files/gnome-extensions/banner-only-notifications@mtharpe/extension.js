// GNOME has no per-app "show the banner but don't keep it in the list" switch. A transient
// notification does exactly that: the shell destroys it once its banner hides. Mark
// notifications from the chosen apps as transient before they reach the message tray.
// If no banner is shown (Do Not Disturb, or banners off for the app), the notification
// stays in the list, so nothing is lost.
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class BannerOnlyNotifications extends Extension {
    enable() {
        this._settings = this.getSettings();
        const settings = this._settings;

        this._injections = new InjectionManager();
        this._injections.overrideMethod(MessageTray.Source.prototype, 'addNotification',
            addNotification => function (notification) {
                // App sources carry a NotificationApplicationPolicy whose id is the app ID
                const appId = this.policy?.id;
                if (appId && settings.get_strv('apps').includes(appId))
                    notification.isTransient = true;
                addNotification.call(this, notification);
            });
    }

    disable() {
        this._injections.clear();
        this._injections = null;
        this._settings = null;
    }
}
