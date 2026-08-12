from __future__ import annotations

from app import StabduebelApp


class FakeChat:
    def __init__(self, last: float = 1.0) -> None:
        self.last = last
        self.seen = []
        self.inserted = []

    def yview(self):
        return (0.0, self.last)

    def see(self, where):
        self.seen.append(where)
        self.last = 1.0

    def configure(self, **_kwargs):
        pass

    def insert(self, *args):
        self.inserted.append(args)


class FakeButton:
    def __init__(self) -> None:
        self.visible = False

    def grid(self):
        self.visible = True

    def grid_remove(self):
        self.visible = False


def shell(last: float = 1.0):
    app = object.__new__(StabduebelApp)
    app.chat = FakeChat(last)
    app.new_message_button = FakeButton()
    app.auto_scroll = True
    app.is_user_near_bottom = True
    return app


def test_user_message_is_always_scrolled_into_view() -> None:
    app = shell(0.3)
    app.auto_scroll = False
    app._append_chat("Sie", "Neue Nachricht")
    assert app.chat.seen == ["end"]
    assert app.auto_scroll is True


def test_assistant_does_not_force_user_down_when_reading_history() -> None:
    app = shell(0.3)
    app.auto_scroll = False
    app._append_chat("Assistent", "Neue Antwort")
    assert app.chat.seen == []
    assert app.new_message_button.visible is True


def test_manual_return_to_bottom_reenables_auto_scroll() -> None:
    app = shell(0.99)
    app.auto_scroll = False
    app.new_message_button.visible = True
    app._update_chat_scroll_state()
    assert app.is_user_near_bottom is True
    assert app.auto_scroll is True
    assert app.new_message_button.visible is False


def test_scroll_up_disables_auto_scroll() -> None:
    app = shell(0.8)
    app._update_chat_scroll_state()
    assert app.is_user_near_bottom is False
    assert app.auto_scroll is False
