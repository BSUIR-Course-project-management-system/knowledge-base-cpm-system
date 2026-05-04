from interface.program_cli import ProgramCLI
from table_api.src.storage import Storage
import time


def main():
    cli = ProgramCLI(Storage())

    print("\n[Успех] Программа собрана! Запуск интерфейса...\n")
    time.sleep(1)
    cli.cmdloop()


if __name__ == "__main__":
    main()
