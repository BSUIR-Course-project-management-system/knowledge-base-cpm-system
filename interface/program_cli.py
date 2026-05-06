import cmd
from rich.console import Console
from typing import TYPE_CHECKING
from datetime import datetime, timedelta
import questionary
import sys
from recomendation_module import RecommendationModule
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager
from schedule_module.src.config_parser import YamlParser
from schedule_module.src.date_checker import DateChecker
from schedule_module.src.datetime_parser import DatetimeParser
from schedule_module.src.schedule_generator import SheduleGenerator
import json

if TYPE_CHECKING:
    from table_api.src.storage import Storage

console = Console()

if sys.platform != "win32":
    try:
        import readline
        import rlcompleter

        # macOS по умолчанию использует libedit, а не GNU readline
        if readline.__doc__ and "libedit" in readline.__doc__:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
    except ImportError:
        pass


class ProgramCLI(cmd.Cmd):
    """Интерактивный консольный интерфейс для программы системы курсовых и дипломных проектов.

    Построен на библиотеке :mod:`cmd.Cmd`. Использует ``rich`` для форматированного вывода и
    ``questionary`` для интерактивного ввода.
    """

    prompt = " \033[1;36m◉ ввод:\033[0m "

    def __init__(self, table_module: "Storage"):
        self._table_module = table_module
        self._is_relevant = False
        self._manager = None
        self._recomendation_module = None
        config_parser = YamlParser()
        dc = DateChecker()
        self._schedule_generator = SheduleGenerator(config_parser, dc)
        super().__init__()

    def _init_recommendation_module(self) -> bool:
        """Ленивая инициализация модуля рекомендаций и поиска.
        Выполняется однократно или после обновления данных из облака.
        """
        if self._recomendation_module is not None:
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
        console.rule(style="blue")
        console.print(r"""[bold dodger_blue1]
                      
                  /wl  )))             
               ./$'$$l    _     _      ██╗   ███╗ ██╗   ███╗ ██████████╗
             _/╝'   $$   /$l   /$l     ██║  ████║ ██║  ████║  ╚══██╔═══╝
           ./╝'     $$ // $$ // $$     ██║ ██╔██║ ██║ ██╔██║     ██║
         ./╝'.•$l   $//   $$/   $$     ██╚██╔╝██║ ██╚██╔╝██║     ██║
       ./╝'    $$  / /  ./ /    $$     ████╔╝ ██║ ████╔╝ ██║     ██║
     ./╝'      $$ /•$$_// $$╔.  $$╔.   ███╔╝  ██║ ███╔╝  ██║     ██║
    |╝'        l$/  ld/╝  l$╝   l$╝    ╚══╝   ╚═╝ ╚══╝   ╚═╝     ╚═╝
    [/bold dodger_blue1]
        """)
        console.print(
            "[bold dodger_blue1]✿ Система поддержки управления курсовыми и дипломными проектами кафедры ✿[/bold dodger_blue1]\n",
            style="frame",
        )
        console.rule(style="blue")
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
        if arg:
            return super().do_help(arg)

        console.print()
        console.print("[bold cyan]Быстрый старт:[/bold cyan]")
        console.print(
            "[green]⦿ update_information[/]   — получить актуальную информацию из облака"
        )
        console.print("[green]⦿ recommend[/]   — рекомендация темы проекта")
        console.print(
            "[green]⦿ schedule_generate[/] — сгенерировать расписание приема опроцентовок для преподавателя(проверяющего)"
        )
        console.print("[green]⦿ list_topics[/]   — вывести список тем")
        console.print("[green]⦿ add_topic[/]   — добавить тему в облако")
        console.print("[green]⦿ remove_topic[/]   — удалить тему из облака")
        console.print("[green]⦿ exit[/]  — выйти из программы\n")

    def _print_topic(self, topic: dict):
        """Вывод информации темы из словаря ``topic``.

        :param topic: Словарь с данными о теме.
        """
        console.print(f"ID: {topic.get('id', 'ID')}")
        console.print(f"Название: {topic.get('topic', 'Неизвестная тема')}")
        console.print(f"Описание: {topic.get('description', 'Нет описания')}")
        console.print(
            f"Занята: {'Да' if topic.get('is_used', 'Не указано') else 'Нет'}"
        )
        console.print(f"Куратор: {topic.get('curator', 'Не указан')}")
        console.print(f"Проверяющий: {topic.get('examiner', 'Не указан')}")
        console.print(f"Дата: {topic.get('date_defence', '??.??.????')}")
        console.print(f"Оценка: {topic.get('rounded_final_grade', 'Нет оценки')}")

    def do_list_topics(self, arg):
        """Получить список тем с возможной сортировкой.

        :param arg: Не используется.
        """
        sort_choices = questionary.select(
            "Выберите тип сортировки тем:",
            choices=["По баллу", "По дате", "Нет сортировки"],
            instruction="Используйте стрелочки(↑↓) — выбор, Enter — подтвердить",
        ).ask()

        if sort_choices is None:
            return
        if "Нет сортировки" not in sort_choices:
            reverse_choice = questionary.select(
                "Выберите тип сортировки тем:",
                choices=["По возрастанию", "По убыванию"],
                instruction="Используйте стрелочки(↑↓) — выбор, Enter — подтвердить",
            ).ask()
        else:
            reverse_choice = ""
        topics: list = json.loads(self._table_module.get_unique_topics())

        sort_reversed: bool = "По убыванию" in reverse_choice

        def safe_grade_key(x):
            g = x.get("rounded_final_grade", 0)
            if g is None:
                return 0
            try:
                return int(g)
            except (ValueError, TypeError):
                return 0

        def safe_date_key(x):
            d = x.get("date_defence")
            if d is None:
                return datetime(1900, 1, 1)
            try:
                return datetime.strptime(str(d), "%d.%m.%Y")
            except (ValueError, TypeError):
                return datetime(1900, 1, 1)

        if "Нет сортировки" in sort_choices:
            pass
        elif "По баллу" in sort_choices:
            topics.sort(key=safe_grade_key, reverse=sort_reversed)
        elif "По дате" in sort_choices:
            topics.sort(key=safe_date_key, reverse=sort_reversed)
        else:
            console.print("Неизвестный выбор. Выбор по-умолчанию: нет сортировки")
        console.rule("Темы", style="blue", characters="=")
        for i, topic in enumerate(topics):
            console.rule(f"Тема № {i + 1}", style="blue")
            self._print_topic(topic)

    def do_remove_topic(self, arg):
        """Удалить тему из Google Sheets хранящимся в облаке.

        :param arg: Не используется.
        """
        is_success = False
        try:
            title = questionary.text(
                "Введите название таблицы или год:", default="ТЕСТ 2026"
            ).ask()
            if title is None or title.strip().lower() == "exit":
                return
            topic = questionary.text("Введите название темы:").ask()
            if topic is None or topic.strip().lower() == "exit":
                return

            with console.status("[bold green]Удаление темы...", spinner="toggle7"):
                self._table_module.remove_topic(
                    key_title=title,
                    topic=topic,
                )
            is_success = True
            self._is_relevant = False

        except KeyboardInterrupt:
            console.print("\n[bold yellow] Удаление прервано пользователем.[/]")
            return
        except Exception as e:
            console.print(f"[bold red] Ошибка в процессе удаления: {e}[/]")
        if is_success:
            console.print("[bold green]Успешное удаление!")

    def do_add_topic(self, arg):
        """Добавить новую тему в Google Sheets хранящимся в облаке.

        :param arg: Не используется.
        """
        is_success = False
        try:
            title = questionary.text(
                "Введите название таблицы или год:", default="ТЕСТ 2026"
            ).ask()
            if title is None or title.strip().lower() == "exit":
                return
            topic = questionary.text("Введите название темы:").ask()
            if topic is None or topic.strip().lower() == "exit":
                return
            description = questionary.text(
                "Введите описание темы (необязательно):", default=""
            ).ask()
            if description is None or description.strip().lower() == "exit":
                return
            curator = questionary.text(
                "Введите куратора (необязательно):", default=""
            ).ask()
            if curator is None or curator.strip().lower() == "exit":
                return
            examiner = questionary.text(
                "Введите проверяющего (необязательно):", default=""
            ).ask()
            if curator is None or curator.strip().lower() == "exit":
                return

            with console.status("[bold green]Добавление темы...", spinner="toggle9"):
                self._table_module.add_topic(
                    key_title=title,
                    topic=topic,
                    description=description,
                    curator=curator,
                    examiner=examiner,
                )
            is_success = True
            self._is_relevant = False

        except KeyboardInterrupt:
            console.print("\n[bold yellow] Добавление прервано пользователем.[/]")
            return
        except Exception as e:
            console.print(f"[bold red] Ошибка в процессе добавления: {e}[/]")
        if is_success:
            console.print("[bold green]Успешное добавление!")

    def do_recommend(self, arg):
        """Поиск рекомендаций по теме по запросу.

        :param arg: Не используется.
        """
        if not self._recomendation_module:
            self._init_recommendation_module()

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
                    if not questionary.confirm("Продолжить поиск?", default=True).ask():
                        break
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
                    recommendations = (
                        self._recomendation_module.search_with_explanations(
                            query=query,
                            n_results=4,
                            max_distance=MAX_DISTANCE,
                            is_used=is_used,
                            curator=curator,
                            examiner=examiner,
                        )
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
        """Генерировать расписание приёма опроцентовок для преподавателя(проверяющего).

        :param arg: Не используется.
        """

        console.rule("Планирование опроцентовок", characters="=", style="blue")
        try:
            project_name = questionary.text("Название проекта: ").ask()

            if project_name is None or project_name.strip().lower() == "exit":
                console.print("[yellow] Название проекта не может быть пустым.")
                return

            reviewer_name = questionary.text("Фамилия и инициалы проверяющего: ").ask()
            if reviewer_name is None or reviewer_name.strip().lower() == "exit":
                console.print(
                    "[yellow] Фамилия и инициалы проверяющего не могут быть пустыми."
                )
                return
            start_date_str = questionary.text("Дата принятия темы (YYYY-MM-DD): ").ask()
            if not DateChecker.is_correct_format(start_date_str):
                console.print("[yellow] Неверный формат даты")
                return
            end_date_str = questionary.text(
                "Конечная дата (защита) (YYYY-MM-DD): "
            ).ask()
            if not DateChecker.is_correct_format(end_date_str):
                console.print("[yellow] Неверный формат даты")
                return

            duration_minutes = questionary.text(
                "Введите продолжительность опроцентовки:",
                validate=lambda text: (
                    (text.isdigit() and int(text) >= 1 and int(text) <= 120)
                    or "Пожалуйста введите число (от 1 до 120)"
                ),
                default="30",
            ).ask()
            if duration_minutes is not None:
                duration_minutes = int(duration_minutes)

            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                hour=self._schedule_generator.WORK_START_HOUR, minute=0
            )
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=self._schedule_generator.WORK_END_HOUR, minute=0
            )

            if end_dt <= start_dt:
                console.print(
                    "[red] Ошибка: конечная дата должна быть позже начальной."
                )
                return
            topics = json.loads(self._table_module.get_unique_topics())
            examiner_found = False
            topic_found = False
            for topic in topics:
                if (
                    not project_name.lower().strip()
                    == topic.get("topic", "").lower().strip()
                ):
                    continue
                topic_found = True
                examiner = topic.get("examiner", "").lower().strip()
                if not examiner:
                    continue
                if reviewer_name.lower().strip() in examiner:
                    examiner_found = True
            if not topic_found:
                console.print("[red] Ошибка: нет такой темы.")
                return
            if not examiner_found:
                console.print(
                    "[red] Ошибка: нет такого проверяющего или он не отвественен за этот проект."
                )
                return

            data = json.loads(self._table_module.get_examiner_schedule(reviewer_name))

            occupied_intervals = DatetimeParser.parse_from_json(data)

            candidates = self._schedule_generator.generate_candidate_starts(
                start_dt, end_dt, duration_minutes, occupied_intervals
            )

            best = self._schedule_generator.select_slots(
                candidates, start_dt, end_dt, num_points=3
            )

            if best is None:
                console.print(
                    "[yellow] Не удалось найти три свободных интервала для опроцентовок."
                )
                return

            console.rule("Результат", characters="=", style="blue")
            console.print(f"Проект: {project_name}")
            console.print(f"Проверяющий: {reviewer_name}")
            for i, start in enumerate(best, start=1):
                end = start + timedelta(minutes=duration_minutes)
                console.print(
                    f"  Опроцентовка {i}: {start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%H:%M')}"
                )
        except KeyboardInterrupt:
            console.print(
                "\n[bold yellow] Генерация опроцентовок прервана пользователем.[/]"
            )
        except Exception as e:
            console.print(f"[bold red] Ошибка в процессе генерации расписания: {e}[/]")

    def do_update_information(self, arg):
        """Обновить данные из облака.

        :param arg: Не используется.
        """
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
