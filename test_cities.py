#!/usr/bin/env python3
"""
Тест для проверки работы areas_cache
"""
import asyncio
from hh_api import HeadHunterAPI
from utils.areas_cache import areas_cache


async def main():
    print("=" * 60)
    print("Тест работы areas_cache")
    print("=" * 60)

    # Загрузка городов
    hh_api = HeadHunterAPI()
    success = await areas_cache.load_areas(hh_api)

    if not success:
        print("❌ Не удалось загрузить города")
        return

    print(f"✅ Загружено городов: {len(areas_cache.areas_index)}")
    print()

    # Тестовые случаи
    test_cases = [
        # (запрос, ожидаемый результат)
        ("Москва", "должен найти ID 1"),
        ("москва", "должен найти ID 1"),
        ("МОСКВА", "должен найти ID 1"),
        ("Питер", "должен найти Санкт-Петербург через алиас"),
        ("СПб", "должен найти Санкт-Петербург через алиас"),
        ("Краснодар", "должен найти Краснодар"),
        ("Владивосток", "должен найти Владивосток"),
        ("Воронеж", "должен найти Воронеж"),
        ("Екб", "должен найти Екатеринбург через алиас"),
        ("Влодивосток", "нечеткий поиск → Владивосток"),
        ("Несуществующий Город", "не должен найти"),
    ]

    print("Тестирование поиска городов:")
    print("-" * 60)

    for city_query, description in test_cases:
        area_id = areas_cache.find_city(city_query)
        if area_id:
            city_name = areas_cache.get_city_name(area_id)
            print(f"✅ '{city_query}' → ID {area_id} ({city_name}) - {description}")
        else:
            print(f"❌ '{city_query}' → Не найден - {description}")

    print()
    print("=" * 60)
    print("Популярные города для LLM:")
    print("-" * 60)
    popular = areas_cache.get_popular_cities()
    print(", ".join(popular[:15]))
    print(f"... всего {len(popular)} городов")
    print("=" * 60)

    await hh_api.close()


if __name__ == "__main__":
    asyncio.run(main())
