// Lists the apps GNOME keeps notification settings for (the same list as
// Settings > Notifications) with a switch each.
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

function notificationApps() {
    const master = new Gio.Settings({schema_id: 'org.gnome.desktop.notifications'});
    const apps = new Map();
    for (const child of master.get_strv('application-children')) {
        const appSettings = new Gio.Settings({
            schema_id: 'org.gnome.desktop.notifications.application',
            path: `/org/gnome/desktop/notifications/application/${child}/`,
        });
        const desktopId = appSettings.get_string('application-id');
        if (!desktopId)
            continue;
        const id = desktopId.replace(/\.desktop$/, '');
        const info = Gio.DesktopAppInfo.new(desktopId);
        apps.set(id, {id, name: info?.get_name() ?? id, icon: info?.get_icon() ?? null});
    }
    return apps;
}

export default class BannerOnlyNotificationsPrefs extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const page = new Adw.PreferencesPage();
        const group = new Adw.PreferencesGroup({
            title: 'Banner-only apps',
            description: 'Notifications from these apps still pop up, but disappear when the ' +
                'banner goes away instead of staying in the notification list. While Do Not ' +
                'Disturb is on they are kept, so you don\'t miss them.',
        });
        page.add(group);
        window.add(page);

        const apps = notificationApps();
        // Keep apps that are switched on but not in GNOME's list (e.g. not installed yet)
        for (const id of settings.get_strv('apps')) {
            if (!apps.has(id))
                apps.set(id, {id, name: id, icon: null});
        }

        const sorted = [...apps.values()].sort((a, b) => a.name.localeCompare(b.name));
        for (const app of sorted) {
            const row = new Adw.SwitchRow({
                title: app.name,
                subtitle: app.id,
                active: settings.get_strv('apps').includes(app.id),
            });
            row.add_prefix(app.icon
                ? new Gtk.Image({gicon: app.icon, pixel_size: 32})
                : new Gtk.Image({icon_name: 'application-x-executable-symbolic', pixel_size: 32}));
            row.connect('notify::active', () => {
                const current = settings.get_strv('apps').filter(id => id !== app.id);
                if (row.active)
                    current.push(app.id);
                settings.set_strv('apps', current);
            });
            group.add(row);
        }
    }
}
