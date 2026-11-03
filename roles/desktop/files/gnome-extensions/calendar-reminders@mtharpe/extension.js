// GNOME Calendar (gnome-calendar-zoom build) sends each event reminder as a notification whose
// "Snooze 10 min" button runs the app action reminder-snooze with (reminder key, when). Here
// that button becomes "Snooze ▾", which opens a choice of times inside the notification, like
// macOS. A choice runs the same app action with its own time; nothing else changes, and every
// other notification is left alone.
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as MessageList from 'resource:///org/gnome/shell/ui/messageList.js';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const SNOOZE_ACTION = 'app.reminder-snooze';
const AT_START = 0;

// [seconds from now (0 = when the event starts), label]
const CHOICES = [
    [[5 * 60, '5 min'], [10 * 60, '10 min'], [15 * 60, '15 min'], [30 * 60, '30 min']],
    [[60 * 60, '1 hour'], [AT_START, 'At start']],
];

// Custom: minutes, stepped finer for short snoozes
const CUSTOM_STEPS = [
    ...Array.from({length: 11}, (_, i) => 5 + i * 5),          // 5 … 55 min
    ...Array.from({length: 13}, (_, i) => 60 + i * 15),        // 1 h … 4 h
    ...Array.from({length: 20}, (_, i) => 300 + i * 60),       // 5 h … 24 h
];
const CUSTOM_START = CUSTOM_STEPS.indexOf(45);

function describeMinutes(minutes) {
    if (minutes < 60)
        return `${minutes} min`;
    const h = Math.floor(minutes / 60), m = minutes % 60;
    return m ? `${h} h ${m} min` : `${h} h`;
}

// The reminder behind a notification: its snooze button's label and key, or null.
function reminderOf(notification) {
    const serialized = notification?._serialized;
    if (!serialized)
        return null;

    try {
        const buttons = serialized.deepUnpack().buttons?.deepUnpack() ?? [];
        for (const button of buttons) {
            if (button.action?.unpack() !== SNOOZE_ACTION)
                continue;
            let target = button.target;
            if (target?.get_type_string() === 'v')
                target = target.unpack();
            const [key] = target.deepUnpack();
            return {label: button.label.unpack(), key};
        }
    } catch (e) {
        logError(e, 'calendar-reminders: unexpected notification');
    }
    return null;
}

function snooze(notification, key, seconds, fallbackAction) {
    const source = notification.source;
    if (typeof source?.activateAction === 'function') {
        source.activateAction('reminder-snooze', new GLib.Variant('(sx)', [key, seconds]));
        notification.destroy();
    } else {
        fallbackAction.activate();   // the app's own "Snooze 10 min"
    }
}

function choiceButton(label, onClicked) {
    const button = new St.Button({
        style_class: 'notification-button',
        x_expand: true,
        can_focus: true,
        label,
    });
    button.connect('clicked', onClicked);
    return button;
}

function buildChoices(message, reminder, action) {
    const box = new St.BoxLayout({orientation: 1 /* vertical */, x_expand: true});
    const choose = seconds => snooze(message.notification, reminder.key, seconds, action);

    for (const row of CHOICES) {
        const line = new St.BoxLayout({x_expand: true, style_class: 'notification-buttons-bin'});
        for (const [seconds, label] of row)
            line.add_child(choiceButton(label, () => choose(seconds)));
        if (row === CHOICES[CHOICES.length - 1]) {
            line.add_child(choiceButton('Custom…', () => {
                custom.visible = !custom.visible;
            }));
        }
        box.add_child(line);
    }

    // Custom: − 45 min + Snooze (buttons only: a banner can't count on keyboard focus)
    let step = CUSTOM_START;
    const custom = new St.BoxLayout({x_expand: true, visible: false, style_class: 'notification-buttons-bin'});
    const value = new St.Label({text: describeMinutes(CUSTOM_STEPS[step]), x_expand: true,
        y_align: 2 /* center */, style: 'text-align: center;'});
    const move = delta => {
        step = Math.max(0, Math.min(CUSTOM_STEPS.length - 1, step + delta));
        value.text = describeMinutes(CUSTOM_STEPS[step]);
    };
    custom.add_child(choiceButton('−', () => move(-1)));
    custom.add_child(value);
    custom.add_child(choiceButton('+', () => move(1)));
    custom.add_child(choiceButton('Snooze', () => choose(CUSTOM_STEPS[step] * 60)));
    box.add_child(custom);

    return box;
}

export default class CalendarReminders extends Extension {
    enable() {
        this._injections = new InjectionManager();
        this._injections.overrideMethod(MessageList.NotificationMessage.prototype, '_addAction',
            addAction => function (action) {
                const reminder = reminderOf(this.notification);
                if (!reminder || action.label !== reminder.label) {
                    addAction.call(this, action);
                    return;
                }

                // Same button row the shell builds, with this row and the choices under it.
                if (!this._buttonBox) {
                    this._buttonBox = new St.BoxLayout({
                        x_expand: true,
                        style_class: 'notification-buttons-bin',
                    });
                    this._snoozeArea = new St.BoxLayout({orientation: 1, x_expand: true});
                    this._snoozeArea.add_child(this._buttonBox);
                    this.setActionArea(this._snoozeArea);
                    global.focus_manager.add_group(this._snoozeArea);
                }

                const button = new St.Button({
                    style_class: 'notification-button',
                    x_expand: true,
                    label: 'Snooze ▾',
                });
                button.connect('clicked', () => {
                    if (!this._snoozeChoices) {
                        this._snoozeChoices = buildChoices(this, reminder, action);
                        if (this._snoozeArea) {
                            this._snoozeArea.add_child(this._snoozeChoices);
                        } else {
                            // The row already existed: put it and the choices together.
                            const area = new St.BoxLayout({orientation: 1, x_expand: true});
                            this._actionBin.set_child(null);
                            area.add_child(this._buttonBox);
                            area.add_child(this._snoozeChoices);
                            this._snoozeArea = area;
                            this.setActionArea(area);
                        }
                        return;
                    }
                    this._snoozeChoices.visible = !this._snoozeChoices.visible;
                });

                this._actions.set(action, button);
                this._buttonBox.insert_child_at_index(button, 0);
            });
    }

    disable() {
        this._injections.clear();
        this._injections = null;
    }
}
