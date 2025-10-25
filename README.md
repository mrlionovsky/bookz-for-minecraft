# bookz-for-minecraft
Утилита для вытаскивания книг из вашего мира на 1.7.10.

Была задача. Интересная. Есть сервер на 1.7.10, работающий уже 15 лет. и было очень интересно почитать, что там игроки понаписали в книгах и вытащить огромный пласт истории. Поэтому и появилась данная утилита.

Инструкции:
1. Установить Python
2. pip install --upgrade nbtlib
3. Прописать в WORLD_DIR имя вашего мира и положить его в папку со скриптом.
4. Запустить скрипт, все книги будут в exported_books/json.
5. Далее книги можно через любую GPT или утилиту по вкусу адаптировать в удобный вам формат. TXT/Mediawiki, etc.

Важно:
1. Ад, энд, другие миры нужно прописывать отдельно - положив DIM1, DIM-1, etc и прописать их на шаге 3.
2. Моды НЕ ПОДДЕРЖИВАЮТСЯ. Только "ванильные" сундуки, диспенсеры, воронки, и т.д. Когда-нибудь я это сделаю. Но не сегодня.
3. В коде прописаны стойки для зелий. Не удивляйтесь! Наши ОПы прятали в версии 1.4 книги в них, чтоб точно никто не спёр.
4. Скан инвертарей игроков выдаёт exception. Я не знаю, криворук ли я, или же как-то лаунчер сашка/моды вносят изменения - но работало только на ванилле.
5. БЭКАП МИРА!!!

Скрипт модифицировать, копировать, распостранять можно свободно, просто оставьте ссылку на мой гитхаб и моё имя. Полезное должно быть открытым.

Пример вывода скрипта:
{
 "title": "Notes on an Icy Cave",
 "author": "A Forgotten Explorer",
 "pages": [
  "§8[[An explorer's notebook, covered in frost]]§0\n\nThe blizzard surrounding these snowy lands is unceasing. This is no ordinary snowfall--this is a magical phenomenon. I will have to conduct experiments to find",
  "what is capable of causing such an effect.\n\n§8[[Next entry]]§0\n\nAt the center of the dark forest, where the leaves turn red and the grass dies, there is a wooden tower. The tops of the tower are affixed with",
  "structures acting as antennae. The antennae are not the source of the snowfall, but serve merely to boost the power of the curse causing it.\n\nA blizzard this intense must be caused by a powerful creature, most likely found",
  "near the top of the dark forest tower. Stop the creature, and the blizzard will fade."
 ],
 "location": "Chest:r.4.12.mca[Int(2403),Int(63),Int(6211)]",
 "count": 1,
 "found_at": "2025-10-25T14:53:00"
}
