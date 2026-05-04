import cmd
from rich.console import Console
from rich.table import Table
from typing import TYPE_CHECKING
import time
import questionary
import readline

from recomendation_module import RecommendationModule
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager

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
        self._manager = None
        self._recomendation_module = None

        super().__init__()

    def _init_recommendation_backend(self) -> bool:
        """Ленивая инициализация модуля рекомендаций и поиска.
        Выполняется однократно или после обновления данных из облака.
        """
        if self._rec_module is not None:
            return True

        try:
            with console.status(
                "[bold green]Инициализация модуля рекомендаций...", spinner="dots"
            ):
                loader = JsonLoader()
                saver = JsonSaver()
                self._manager = ThemeFinderManager(loader, saver)
                self._manager.process_data()
                self._manager.prepare_search()
                self._recomendation_module = RecommendationModule(
                    search_manager=self._manager
                )
            console.print("[bold green] Модуль успешно загружен![/]")
            return True
        except Exception as e:
            console.print(f"[bold red] Ошибка инициализации: {e}[/]")
            return False

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
        """Обёртка над cmdloop для корректной обработки KeyboardInterrupt."""
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
        console.print("- [green]recommend[/]   — рекомендация темы проекта")
        console.print(
            "- [green]schedule_generate[/] — сгенерировать расписание приема опроцентовок для преподавателя(проверяющего)"
        )
        console.print(
            "- [green]update_information[/]   — получить актуальную информацию из облака"
        )
        console.print("- [green]exit[/]  — выйти из программы\n")

    def do_recomend(self, arg):
        if not self._init_recommendation_backend():
            return
        console.print(
            "[bold cyan] Режим рекомендаций. Нажмите Ctrl+C или введите 'exit' для выхода.[/]"
        )
        while True:
            try:
                query = questionary.text("Введите запрос для поиска:").ask()
                if query is None or query.strip().lower() == "exit":
                    break
                query = query.strip()
                if not query:
                    console.print("[yellow]Запрос не может быть пустым.[/]")
                    continue

                occupation_choices = questionary.checkbox(
                    "Выберите тип тем по занятости:",
                    choices=["Занятые", "Свободные"],
                    instruction="Пробел — выбрать/снять, Enter — подтвердить",
                ).ask()

                if occupation_choices is None:
                    break

                if (
                    "Занятые" in occupation_choices
                    and "Свободные" in occupation_choices
                ):
                    is_used = None
                elif "Свободные" in occupation_choices:
                    is_used = False
                elif "Занятые" in occupation_choices:
                    is_used = True
                else:
                    is_used = None

                # 3. Куратор
                curator = questionary.text("Имя куратора (Enter, если не важно):").ask()
                curator = curator.strip() if curator else None

                # 4. Проверяющий
                examiner = questionary.text(
                    "Имя проверяющего (Enter, если не важно):"
                ).ask()
                examiner = examiner.strip() if examiner else None

                # 5. Выполнение поиска
                with console.status(
                    "[bold green]Поиск и генерация описаний...", spinner="dots"
                ):
                    recommendations = self._rec_module.search_with_explanations(
                        query=query,
                        n_results=4,
                        max_distance=MAX_DISTANCE,
                        is_used=is_used,
                        curator=curator,
                        examiner=examiner,
                    )

                if not recommendations:
                    console.print(
                        "[yellow] Ничего не найдено. Попробуйте изменить параметры поиска.[/]"
                    )
                    continue

                console.print("\n[bold magenta] Подробные описания найденных тем:[/]")
                for idx, rec in enumerate(recommendations, start=1):
                    console.rule(f"[bold cyan]Тема {idx}[/]")
                    console.print(rec.get("topic_description_text", "Нет описания"))

                # 6. Продолжить или выйти
                if not questionary.confirm("Продолжить поиск?", default=True).ask():
                    break

            except KeyboardInterrupt:
                console.print("\n[bold yellow] Поиск прерван пользователем.[/]")
                break
            except Exception as e:
                console.print(f"[bold red] Ошибка в процессе поиска: {e}[/]")

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
