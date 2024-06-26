from abc import ABC

class Module(ABC):
    """
    Интерфейс, описывающий модуль и доступные ему "хуки".
    """

    def on_start(self, plugin_dir):
        """
        Вызывается при старте плагина.
        """

    def draw_settings(self, parent_widget, cmdr, is_beta, position):
        """
        Вызывается при отрисовки окна настроек.
        """

    def on_settings_changed(self, cmdr, is_beta):
        """
        Вызывается в момент, когда пользователь
        сохраняет настройки.
        """

    def on_journal_entry(self, entry):
        """
        Вызывается при появлении новой записи в логах.
        """

    def on_cmdr_data(self, data, is_beta):
        """
        Вызывается при появлении новых данных о командире.
        """

    def on_dashboard_entry(self, cmdr, is_beta, entry):
        """
        Вызывается при обновлении игрой status.json
        """

    def on_chat_message(self, entry):
        """
        Вызывается при появлении новой записи типа сообщения в логах.
        """

    def close(self):
        """
        Вызывается в момент завершения работы плагина.
        """

    @property
    def enabled(self) -> bool:
        """
        Сообщает, включен ли плагин.
        """
        return True
