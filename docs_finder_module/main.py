from search_client import search_semantic_scholar


def main():
    print("Поиск научных публикаций\n")

    topic = input("Введите тему исследования (русский или английский): ").strip()
    if not topic:
        print("Тема не должна быть пустой.")
        return

    raw_limit = input("Сколько результатов показать? [5]: ").strip()
    try:
        limit = int(raw_limit) if raw_limit else 5
        if limit < 1:
            raise ValueError
    except ValueError:
        print("Некорректное число. Использую 5.")
        limit = 5

    print(f"\nИщу публикации по теме: «{topic}»...\n")
    papers = search_semantic_scholar(topic, max_results=limit, include_sources=True)

    if not papers:
        print("Публикации не найдены или поисковые сервисы временно недоступны.")
        print("Попробуйте сформулировать тему короче или повторить поиск позже.")
        return

    print(f"Найдено публикаций: {len(papers)}\n")
    print("=" * 88)

    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Источник/журнал: {paper['categories']}")
        print(f"   Авторы: {paper['authors']}")
        print(f"   Год: {paper['date']}")
        print(f"   База: {paper.get('source', 'не указана')}")
        print(f"   DOI/ссылка: {paper['url'] or 'ссылка недоступна'}")
        print(f"   Аннотация: {paper['abstract']}")
        print("-" * 88)


if __name__ == "__main__":
    main()
