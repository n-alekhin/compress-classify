import os
import subprocess
import shutil
import logging
import tempfile
import importlib.util
import random
import re
import json
import platform
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

parser = argparse.ArgumentParser(
    description="Скрипт отладки ядер классификации"
)
parser.add_argument(
    "--root-folder", "-r",
    required=True,
    help="Путь к корневой папке с тестовыми текстами"
)
parser.add_argument(
    "--cores-folder", "-c",
    required=True,
    help="Путь к папке с ядрами в .7z"
)
parser.add_argument(
    "--test-folder", "-t",
    required=True,
    help="Путь к папке с кандидатами для отладки"
)
parser.add_argument(
    "--max-debug-articles", "-n",
    type=int,
    default=5,
    help="Максимальное число статей в ядре при отладке"
)
parser.add_argument(
    "--max-workers", "-w",
    type=int,
    default=4,
    help="Число потоков при классификации"
)
args = parser.parse_args()

ROOT_FOLDER         = args.root_folder
CORES_FOLDER        = args.cores_folder
TEST_FOLDER         = args.test_folder
MAX_DEBUG_ARTICLES  = args.max_debug_articles
MAX_WORKERS         = args.max_workers

logging.basicConfig(
    filename='classification.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
class NoByteFilter(logging.Filter):
    def filter(self, record):
        return 'байт' not in record.getMessage()
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.addFilter(NoByteFilter())
logger = logging.getLogger(__name__)

CLASSIFY_SCRIPT_PATH = 'Classification.py'
if platform.system() == "Windows":
    ZIP_TOOL = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "tools", "7zip", "7za.exe"
    )
else:
    ZIP_TOOL = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "tools", "7zip", "7z"
    )

spec = importlib.util.spec_from_file_location('classify_mod', CLASSIFY_SCRIPT_PATH)
classify_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classify_mod)
logging.getLogger('classify_mod').setLevel(logging.WARNING)

def compute_accuracy_per_category(root_folder, cores_folder, zip_tool):
    zip_cores = {
        os.path.splitext(f)[0]: os.path.join(cores_folder, f)
        for f in os.listdir(cores_folder) if f.endswith('.7z')
    }
    per_total, per_correct = {}, {}
    for cat in os.listdir(root_folder):
        path = os.path.join(root_folder, cat)
        if not os.path.isdir(path):
            continue
        per_total[cat] = per_correct[cat] = 0
        for fn in os.listdir(path):
            if not fn.endswith('.txt'):
                continue
            pred = classify_mod.classify_text_with_zips(
                zip_tool, zip_cores, os.path.join(path, fn),
                max_workers=MAX_WORKERS
            )
            per_total[cat] += 1
            if pred == cat:
                per_correct[cat] += 1
    return {
        c: (per_correct[c] / per_total[c] * 100) if per_total[c] else 0
        for c in per_total
    }

def create_7z_archive(output_archive, texts, zip_tool, category_name=None):
    output_archive = os.path.abspath(output_archive)
    if os.path.exists(output_archive):
        os.remove(output_archive)
    with tempfile.TemporaryDirectory() as tmpdir:
        if category_name:
            workdir = os.path.join(tmpdir, category_name)
            os.makedirs(workdir, exist_ok=True)
            for txt in texts:
                shutil.copy(txt, workdir)
            subprocess.run(
                [zip_tool, "a", output_archive, category_name],
                cwd=tmpdir, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        else:
            for txt in texts:
                shutil.copy(txt, tmpdir)
            subprocess.run(
                [zip_tool, "a", output_archive, "."],
                cwd=tmpdir, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

def evaluate_category_accuracy(zip_cores, category, root_folder, zip_tool):
    cat_dir = os.path.join(root_folder, category)
    total = correct = 0
    for fn in os.listdir(cat_dir):
        if not fn.endswith('.txt'):
            continue
        pred = classify_mod.classify_text_with_zips(
            zip_tool, zip_cores, os.path.join(cat_dir, fn),
            max_workers=MAX_WORKERS
        )
        total += 1
        if pred == category:
            correct += 1
    return (correct / total * 100) if total else 0

def debug_core(category, target_size=MAX_DEBUG_ARTICLES):
    logger.info(f"=== Отладка для ядра «{category}», target={target_size} ===")
    chk = f"checkpoint_{category}.json"
    cand_dir = os.path.join(TEST_FOLDER, category)
    candidates = [
        os.path.join(cand_dir, f)
        for f in os.listdir(cand_dir) if f.endswith('.txt')
    ]

    extract_root = tempfile.mkdtemp(prefix='stubs_')
    stub_pool = []
    for arc in os.listdir(CORES_FOLDER):
        if not arc.endswith('.7z'):
            continue
        core_name = os.path.splitext(arc)[0]
        out_dir = os.path.join(extract_root, core_name)
        os.makedirs(out_dir, exist_ok=True)
        subprocess.run(
            [ZIP_TOOL, 'x', os.path.join(CORES_FOLDER, arc), f'-o{out_dir}'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        for root, _, files in os.walk(out_dir):
            for f in files:
                if f.endswith('.txt'):
                    stub_pool.append(os.path.join(root, f))
    logger.info(f"Stub pool: {len(stub_pool)} файлов")

    if os.path.exists(chk):
        try:
            with open(chk, 'r', encoding='utf-8') as f:
                state = json.load(f)
            selected  = [os.path.join(cand_dir, fn) for fn in state['selected']]
            remaining = set(os.path.join(cand_dir, fn) for fn in state['remaining'])
            iteration = state['iteration']
            logger.info(f"Чекпоинт загружен: ит={iteration}, sel={len(selected)}, rem={len(remaining)}")
        except Exception:
            logger.warning(f"Не удалось прочитать {chk}, старт заново")
            selected, remaining, iteration = [], set(candidates), 1
    else:
        selected, remaining, iteration = [], set(candidates), 1
        logger.info("Начало без чекпоинта")

    needed = target_size - len(selected)
    stub_set = set()
    if needed > 0:
        if needed > len(stub_pool):
            logger.warning(f"Нужны {needed}, а stub’ов всего {len(stub_pool)}")
            needed = len(stub_pool)
        stub_set = set(random.sample(stub_pool, needed))
        logger.info(f"Добавлено {needed} stub’ов")

    while len(selected) < min(target_size, len(candidates)) and remaining:
        best, best_acc = None, -1.0
        for txt in list(remaining):
            cores = {
                os.path.splitext(f)[0]: os.path.join(CORES_FOLDER, f)
                for f in os.listdir(CORES_FOLDER) if f.endswith('.7z')
            }
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.7z')
            temp_archive = tmpf.name
            tmpf.close()
            create_7z_archive(
                temp_archive,
                list(stub_set) + selected + [txt],
                ZIP_TOOL,
                category_name=category
            )
            cores[category] = temp_archive

            acc = evaluate_category_accuracy(cores, category, ROOT_FOLDER, ZIP_TOOL)
            logger.info(f"Ит{iteration}: пробуем «{os.path.basename(txt)}» → {acc:.2f}%")
            os.remove(temp_archive)

            if acc > best_acc:
                best_acc, best = acc, txt

        if not best:
            logger.warning(f"Ит{iteration}: нет улучшений, выходим")
            break

        removed_stub = None
        if stub_set:
            removed_stub = random.choice(list(stub_set))
            stub_set.remove(removed_stub)

        selected.append(best)
        remaining.remove(best)
        logger.info(
            f"Ит{iteration}: выбрано «{os.path.basename(best)}» "
            f"(acc={best_acc:.2f}%), удалён stub «{os.path.basename(removed_stub) if removed_stub else '-'}»"
        )

        state = {
            'selected':  [os.path.basename(p) for p in selected],
            'remaining': [os.path.basename(p) for p in remaining],
            'iteration': iteration + 1
        }
        with open(chk, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info(f"Чекпоинт сохранён (ит={iteration + 1})")
        iteration += 1

    final = os.path.join(CORES_FOLDER, f"{category}.7z")
    create_7z_archive(final, selected, ZIP_TOOL, category_name=category)
    if os.path.exists(chk):
        os.remove(chk)
        logger.info(f"Чекпоинт {chk} удалён")
    logger.info(f"=== Готово: в ядре «{os.path.basename(final)}» {len(selected)} статей ===")

def main():
    accs = compute_accuracy_per_category(ROOT_FOLDER, CORES_FOLDER, ZIP_TOOL)
    worst = min(accs, key=accs.get)
    logger.info(f"Worst core={worst} acc={accs[worst]:.2f}%")
    debug_core(worst)

if __name__ == '__main__':
    main()
