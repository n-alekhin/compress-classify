# compress-classify-test

В данном репозитории представлены скрипты для проверки метода классификации на основе компрессии, применённого к статьям из CyberLeninka и arXiv

для Linux/macOS после клонирования, убедитесь, что Linux-бинар 7z убедитесь имеет права на исполнение
```markdown
chmod +x tools/7zip/7z
```
Вначале запустите скрипт для загрузки библиотек: Install.py
Затем скачайте архив 
```markdown
https://www.7-zip.org/a/7z2409-extra.7z. 
```
Распакуйте его и перенесите 7za.exe в папку tools.

# CyberLeninka
Затем запустите скрипт DownloaderCyberLeninka.py, который скачивает статьи.
```markdown
python DownloaderCyberLeninka.py -n 6
```
-n: количество статей в каждую тему.
Запустите CoreCreater.py. Он сформирует ядро.
```markdown
python CoreCreater.py -n 2 -s Articless -o Cores
```
-n: количество статей в каждое ядро.
-s: Директория из которой берем статьи для ядра.
-o: Название папки в которой будут находиться ядра.
Далее предлагается запустить Classification.py. Он классифицирует статьи из Articless.
```markdown
python Classification.py -r Articless -c Cores
```
-r: Директория со статьями которые будут проклассифицированы в результате тестов.
-c: Директория с ядрами.
Результат можно посмотреть в classification2.log.
Далее для проверки работоспоспособности оптимизации нужно запустить Sup.py. Теперь в Articless2 находятся статьи кандидаты.
```markdown
python Sup.py 2
```
Теперь запустите DebugCores.py. Он "продебажит" худшее ядро.
```markdown
python DebugCores.py -t "Articless2" -r "Articless" -c "Cores" -n 3
```
-t: Директория с кандидатами в новое оптимизированное ядро.
-r: Директория со статьями для прогона тестов.
-c: Директория с ядрами.
-n: Количество статей которого хотим достичь в ядре после оптимизации.
Логи можно посмотреть в classification.log. Процент точности находится в конце лога

Для классификации 1 статьи запустите следующую команду:
```markdown
python ClassificationOneArticless.py -c "Cores" -i {название файла.txt}
```
-c: Директория с ядрами.
-i: Путь к файлу для классификации 




# arXiv
Запустите скрипт DownloaderArxiv.py. Он скачивает PDF-статьи с arXiv.
Первый аргумент колличество статей для каждой темы, второй директория куда будут скачиваться файлы
```markdown
python DownloaderArxiv.py 5 Articless_pdf
```

Запустите скрипт totxt.py. Скрипт конвертирует скачанные PDF в текст. Берёт все .pdf из одной директории , Извлекает содержимое и сохраняет в .txt, Разбивает результаты на папки по темам. И сохраняет в другой директории
Первый аргумент директория со статьями в pdf, второй директория куда будут сохраняться статьи в txt.
```markdown
python totxt.py Articless_pdf Articless_ArXiv
```

После запустите Sup.py. Он отделит часть статей для формирования ядра.
Первый аргумент директория со статьями, второй директория куда будут пеноситься статьи для формирования ядра.
```markdown
python Sup.py 4 Articless_ArXiv Articless_ArXiv_2
```

Для опимизации состава ядра вместо обычного формирования ядра запустите скрипт updateCore.py. Выполнение скрипта может занять много времени при большом колличестве статей.
Первый аргумент колличество статей в ядре. второй аргумент директория со статьями для формирования ядра. тертий куда сохранять ядра.
python updateCore.py
```markdown
python updateCore.py 3 Articless_ArXiv_2 Cores_ArXiv
```

Вместо прошлого скрипта можно запустите CoreCreater.py. Он сформирует ядро.
```markdown
python CoreCreater.py -n 4 -s Articless_ArXiv_2 -o Cores_ArXiv
```
-n: количество статей в каждое ядро.
-s: Директория из которой берем статьи для ядра.
-o: Название папки в которой будут находиться ядра.


Далее предлагается запустить Classification.py. Он классифицирует статьи из Articless.
```markdown
python Classification.py -r Articless_ArXiv -c Cores_ArXiv
```
-r: Директория со статьями которые будут проклассифицированы в результате тестов.
-c: Директория с ядрами.
Результат можно посмотреть в classification2.log. Процент точности находится в конце лога

Для класификации одной статьи. 
Сначало нужно перевести статью в txt. Для этого нужно запустить скрипт totxtOneArticless
Первый аргумент путь к файлу pdf. если есть пробелы нужно обернуть в кавычки
```markdown
python totxtOneArticless.py {название файла.pdf}
```

Для классификации 1 статьи запустите следующую команду:
```markdown
python ClassificationOneArticless.py -c "Cores_ArXiv" -i {название файла.txt}
```
-c: Директория с ядрами.
-i: Путь к файлу для классификации. Если есть пробелы нужно обернуть в кавычки

