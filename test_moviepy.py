# test_moviepy.py
try:
    import moviepy
    print(f"moviepy успешно импортирован. Версия: {moviepy.__version__}")
    print(f"Путь к модулю: {moviepy.__file__}")

    print("\nПроверка импорта moviepy.editor...")
    try:
        from moviepy.editor import VideoFileClip
        print("VideoFileClip успешно импортирован")
    except ImportError as e:
        print(f"Ошибка импорта VideoFileClip: {e}")

    print("\nСписок доступных модулей в moviepy:")
    import pkgutil
    for loader, name, is_pkg in pkgutil.iter_modules(moviepy.__path__):
        print(f"- {name} ({'пакет' if is_pkg else 'модуль'})")

except ImportError as e:
    print(f"Ошибка импорта moviepy: {e}")