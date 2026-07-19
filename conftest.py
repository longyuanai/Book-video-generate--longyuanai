"""pytest 根配置：把仓库根目录加入 sys.path，保证裸 `pytest` 也能导入 bazi 等模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
