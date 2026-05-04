import cmd
from rich.console import Console
from rich.table import Table
from typing import TYPE_CHECKING
import time
import questionary
import readline

if TYPE_CHECKING:
    from table_api.src.storage import Storage
console = Console()

# Auto-complete commands for Mac/Linux
if readline.__doc__ and "libedit" in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")


class ProgramCLI(cmd.Cmd):
    """Интерактивный консольный интерфейс для программы системы курсовых и дипломных проектов.

    Построен на библиотеке :mod:`cmd.Cmd`. Использует ``rich`` для форматированного вывода и
    ``questionary`` для интерактивного ввода.
    """

    prompt = " \033[1;36m*ввод:\033[0m "

    def __init__(self, table_module: "Storage"):
        self._table_module = table_module
        self._is_relevant = False
        super().__init__()

    def preloop(self):
        """Вывод ASCII-арта логотипа и подсказка для быстрого-старта перед входом в командный цикл."""
        console.clear()
        console.print(r"""[bold dodger_blue1]
------------------------------------------------------------------------
                      
                  /wl               
               ./# ##l    _     _      ██╗   ███╗ ██╗   ███╗ ██████████║
             _/╝    ##   /#l   /#l     ██║  ████║ ██║  ████║     ██╔═══╝
           ./╝      ## // ## // ##     ██║ ██╔██║ ██║ ██╔██║     ██║
         ./╝ .•#l   ##/   ##/   ##     ██╚██╔╝██║ ██╚██╔╝██║     ██║
       ./╝     ##   ##  _/##    ##     ████╔╝ ██║ ████╔╝ ██║     ██║
     ./╝       ## /•##_// ##╔.  ##╔.   ███╔╝  ██║ ███╔╝  ██║     ██║
    |╝         l#/  ld/╝  l#╝   l#╝    ╚══╝   ╚═╝ ╚══╝   ╚═╝     ╚═╝
                      
    [/bold dodger_blue1]
        """)
        console.print(
            "[bold dodger_blue1]✿ Система поддержки управления курсовыми и дипломными проектами кафедры ✿[/bold dodger_blue1]\n",
            style="frame",
        )
        console.print(
            "? Напишите [dodger_blue1]help[/] или [dodger_blue1]?[/] для списка команд.\n"
        )

    def cmdloop(self, intro=""):
        while True:
            try:
                super().cmdloop(intro="")
                break
            except KeyboardInterrupt:
                print("^C")
                self.do_exit("")
                return True

    def do_help(self, arg):
        """Показать стандартный листинг помощи, а затем вывод сводка команд для быстрого-старта.

        :param arg: Команда для которой нужно получить помощь.
        :type arg: str
        """
        # if arg:
        #     return super().do_help(arg)

        # super().do_help(arg)

        console.print()
        console.print("[bold cyan]Быстрый старт:[/bold cyan]")
        console.print("- [green]topic_search[/]   — поиск темы")
        console.print(
            "- [green]schedule_generate[/] — сгенерировать расписание приема опроцентовок для преподавателя(проверяющего)"
        )
        console.print(
            "- [green]update_information[/]   — получить актуальную информацию из облака"
        )
        console.print("- [green]exit[/]  — выйти из программы\n")

    def do_topic_search(self, arg):
        pass

    def do_schedule_generate(self, arg):
        pass

    def do_update_information(self, arg):
        if self._is_relevant:
            console.print("[bold green]Данные уже актуальны.")
            return
        is_success = False
        with console.status(
            "[bold green]Скачивание данных из облака...", spinner="aesthetic"
        ) as status:
            try:
                self._table_module.update_data_from_cloud()
                status.update("[bold yellow]Распаковка таблиц...")
                status.update("[bold yellow]Упорно парсим в JSON...")
                is_success = True
                self._is_relevant = True
            except Exception as e:
                console.print(
                    "[bold yellow]Непредвиденная ошибка при загрузке данных.[/] \n[yellow]Попробуйте еще раз или обратитесь к разработчикам :)[/]"
                )
                console.print(f"[bold red]:warning: Ошибка:{e}[/]")
        if is_success:
            console.print("[bold green]Успешно! Все данные актуальны!..")

    def do_exit(self, arg):
        """Выход из CLI и остановка программы.

        :param arg: Не используется.
        :type arg: str
        :return: ``True`` для сигнала :meth:`cmd.Cmd.cmdloop` об остановке программы.
        :rtype: bool
        """
        console.print(
            "[bold red]Выход из программы...[/bold red]\n[bold]До новых встреч![/]\n"
        )
        return True
