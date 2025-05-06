"""
行业管理器模块，负责管理股票行业分类数据
"""
import os
import json
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from threading import Lock
from PyQt5.QtCore import QObject, pyqtSignal
from core.logger import LogManager
import traceback


class IndustryManager(QObject):
    """行业管理器类"""
    # 定义信号
    industry_updated = pyqtSignal()  # 行业数据更新信号
    update_error = pyqtSignal(str)   # 更新错误信号

    def __init__(self, config_dir: str = "", cache_file: str = "industry_cache.json", log_manager: Optional[LogManager] = None):
        """初始化行业管理器

        Args:
            config_dir: 配置目录
            cache_file: 缓存文件名
        """
        self.log_manager = log_manager or LogManager()
        self.log_manager.info(f"初始化行业管理器")
        super().__init__()
        self.config_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config")
        self.cache_file = os.path.join(self.config_dir, cache_file)
        self.cache_lock = Lock()
        self.industry_data = {}
        self.last_update_time = None
        self.update_interval = timedelta(days=1)  # 默认1天更新一次

        # 创建配置目录
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

        # 加载缓存数据
        self.load_cache()

    def load_cache(self) -> None:
        """加载缓存数据"""
        try:
            if os.path.exists(self.cache_file):
                with self.cache_lock:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not content.strip():
                            # 文件为空，自动重新拉取
                            self.log_manager.warning("行业数据缓存文件为空，自动重新获取行业数据")
                            self.update_industry_data(True)
                            return

                        try:
                            data = json.loads(content)
                        except Exception as e:
                            self.log_manager.error(
                                f"行业数据缓存文件损坏，自动删除并重新获取: {str(e)}")
                            os.remove(self.cache_file)
                            self.update_industry_data(True)
                            return

                        self.industry_data = data.get('industry_data', {})
                        last_update = data.get('last_update')
                        if last_update:
                            self.last_update_time = datetime.fromisoformat(
                                last_update)
        except Exception as e:
            self.log_manager.error(f"加载行业数据缓存失败: {str(e)}")
            self.log_manager.info(f"自动重新获取行业数据！！！！")
            os.remove(self.cache_file)
            self.update_industry_data(True)

    def save_cache(self) -> None:
        """保存缓存数据"""
        try:
            # with self.cache_lock:
            data = {
                'industry_data': self.industry_data,
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_manager.error(f"保存行业数据缓存失败: {str(e)}")

    def _get_eastmoney_industry_data(self) -> Dict:
        """获取东方财富行业分类和板块数据

        Returns:
            Dict: 包含行业和板块数据的字典
        """
        try:
            # 基础配置
            base_url = "http://push2.eastmoney.com/api/qt/clist/get"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            base_params = {
                "pn": "1",
                "pz": "5000",  # 获取足够多的数据
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fields": "f12,f14,f100,f103,f104,f105,f106",  # 增加f104:概念板块 f105:地域板块 f106:主题板块
            }

            result = {}

            # 1. 获取A股行业数据
            industry_params = base_params.copy()
            # A股
            industry_params["fs"] = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

            response = requests.get(
                base_url, headers=headers, params=industry_params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        csrc_industry = item.get('f100', '')  # 证监会行业
                        exchange_industry = item.get('f103', '')  # 交易所行业
                        concept_sector = item.get('f104', '')  # 概念板块
                        region_sector = item.get('f105', '')  # 地域板块
                        theme_sector = item.get('f106', '')  # 主题板块

                        # 确定市场类型
                        market = 'SH' if code.startswith(('600', '601', '603', '605', '688')) else \
                            'SZ' if code.startswith(('000', '001', '002', '003', '300')) else \
                            'BJ' if code.startswith(
                            ('4', '8')) else 'OTHER'

                        result[code] = {
                            'code': code,
                            'name': name,
                            'csrc_industry': csrc_industry,
                            'exchange_industry': exchange_industry,
                            'market': market,
                            'sectors': {
                                'concept': concept_sector.split(',') if concept_sector else [],
                                'region': region_sector.split(',') if region_sector else [],
                                'theme': theme_sector.split(',') if theme_sector else []
                            }
                        }

            # 2. 获取概念板块数据
            concept_params = base_params.copy()
            concept_params["fs"] = "m:90+t:3"  # 概念板块

            response = requests.get(
                base_url, headers=headers, params=concept_params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        if code not in result:
                            result[code] = {
                                'code': code,
                                'name': name,
                                'type': 'concept',
                                'market': 'CONCEPT'
                            }

            # 3. 获取地域板块数据
            region_params = base_params.copy()
            region_params["fs"] = "m:90+t:1"  # 地域板块

            response = requests.get(
                base_url, headers=headers, params=region_params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        if code not in result:
                            result[code] = {
                                'code': code,
                                'name': name,
                                'type': 'region',
                                'market': 'REGION'
                            }

            # 4. 获取主题板块数据
            theme_params = base_params.copy()
            theme_params["fs"] = "m:90+t:2"  # 主题板块

            response = requests.get(
                base_url, headers=headers, params=theme_params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        if code not in result:
                            result[code] = {
                                'code': code,
                                'name': name,
                                'type': 'theme',
                                'market': 'THEME'
                            }

            # 5. 获取指数板块数据
            index_params = base_params.copy()
            index_params["fs"] = "m:1+s:2,m:0+s:6"  # 指数板块

            response = requests.get(
                base_url, headers=headers, params=index_params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        if code not in result:
                            result[code] = {
                                'code': code,
                                'name': name,
                                'type': 'index',
                                'market': 'INDEX'
                            }

            self.log_manager.info(f"获取东方财富数据完成，共 {len(result)} 条记录")
            return result

        except Exception as e:
            self.log_manager.error(f"获取东方财富数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return {}

    def update_industry_data(self, force: bool = False) -> bool:
        """更新行业数据

        Args:
            force: 是否强制更新

        Returns:
            更新是否成功
        """
        try:
            # 检查是否需要更新
            if not force and self.last_update_time:
                if datetime.now() - self.last_update_time < self.update_interval:
                    return True

            # 优先从东方财富获取数据
            new_data = self._get_eastmoney_industry_data()

            # 如果东方财富数据获取失败，尝试从交易所获取
            if not new_data:
                # 上交所行业分类
                sh_data = self._get_sh_industry_data()
                # 深交所行业分类
                sz_data = self._get_sz_industry_data()
                # 北交所行业分类
                bj_data = self._get_bj_industry_data()

                # 合并数据
                new_data = {}
                new_data.update(sh_data)
                new_data.update(sz_data)
                new_data.update(bj_data)

            if new_data:
                # with self.cache_lock:
                self.industry_data = new_data
                self.last_update_time = datetime.now()
                self.save_cache()

                # 发送更新信号
                self.industry_updated.emit()
                return True

            return False

        except Exception as e:
            error_msg = f"更新行业数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.update_error.emit(error_msg)
            return False

    def _get_sh_industry_data(self) -> Dict:
        """获取上交所行业分类数据"""
        try:
            # 上交所行业分类接口
            url = "http://query.sse.com.cn/security/stock/getStockListData.do"
            headers = {
                "Referer": "http://www.sse.com.cn/",
                "User-Agent": "Mozilla/5.0"
            }
            params = {
                "jsonCallBack": "jsonpCallback",
                "isPagination": "true",
                "stockCode": "",
                "csrcCode": "",
                "areaName": "",
                "stockType": 1,
                "pageHelp.cacheSize": 1,
                "pageHelp.beginPage": 1,
                "pageHelp.pageSize": 2000,
                "_": int(time.time() * 1000)
            }

            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                # 解析数据
                text = response.text
                json_str = text[text.find('{'):text.rfind('}')+1]
                data = json.loads(json_str)

                result = {}
                for item in data['result']:
                    code = item['SECURITY_CODE_A']
                    csrc_industry = item.get('CSRC_CODE_DESC', '')
                    ssein_industry = item.get('SSEIN_CODE_DESC', '')
                    result[code] = {
                        'code': code,
                        'name': item['SECURITY_ABBR_A'],
                        'csrc_industry': csrc_industry,  # 证监会行业
                        'exchange_industry': ssein_industry,  # 交易所行业
                        'market': 'SH'
                    }
                return result

            return {}

        except Exception as e:
            print(f"获取上交所行业数据失败: {str(e)}")
            return {}

    def _get_sz_industry_data(self) -> Dict:
        """获取深交所行业分类数据"""
        try:
            # 深交所行业分类接口
            url = "http://www.szse.cn/api/report/ShowReport"
            params = {
                "SHOWTYPE": "JSON",
                "CATALOGID": "1110",
                "TABKEY": "tab1",
                "random": str(time.time())
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()

                result = {}
                for item in data[0]['data']:
                    code = item['证券代码']
                    industry = item.get('所属行业', '')
                    result[code] = {
                        'code': code,
                        'name': item['证券简称'],
                        'csrc_industry': industry,
                        'market': 'SZ'
                    }
                return result

            return {}

        except Exception as e:
            print(f"获取深交所行业数据失败: {str(e)}")
            return {}

    def _get_bj_industry_data(self) -> Dict:
        """获取北交所行业分类数据"""
        try:
            # 北交所行业分类接口
            url = "http://www.bse.cn/nqhqController/nqhq.do"
            params = {
                "page": "1",
                "size": "1000",
                "category": "industry"
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()

                result = {}
                for item in data['content']:
                    code = item['securityCode']
                    industry = item.get('industry', '')
                    result[code] = {
                        'code': code,
                        'name': item['securityName'],
                        'csrc_industry': industry,
                        'market': 'BJ'
                    }
                return result

            return {}

        except Exception as e:
            print(f"获取北交所行业数据失败: {str(e)}")
            return {}

    def get_industry(self, stock_code: str) -> Optional[Dict]:
        """获取股票行业信息

        Args:
            stock_code: 股票代码

        Returns:
            行业信息字典
        """
        return self.industry_data.get(stock_code)

    def get_stocks_by_industry(self, industry: str) -> List[str]:
        """获取指定行业的所有股票

        Args:
            industry: 行业名称

        Returns:
            股票代码列表
        """
        result = []
        for code, info in self.industry_data.items():
            if info.get('csrc_industry') == industry or info.get('exchange_industry') == industry:
                result.append(code)
        return result

    def get_all_industries(self) -> List[str]:
        """获取所有行业列表

        Returns:
            行业名称列表
        """
        industries = set()
        for info in self.industry_data.values():
            if info.get('csrc_industry'):
                industries.add(info['csrc_industry'])
            if info.get('exchange_industry'):
                industries.add(info['exchange_industry'])
        return sorted(list(industries))

    def export_industry_data(self, file_path: str) -> bool:
        """导出行业数据

        Args:
            file_path: 导出文件路径

        Returns:
            是否导出成功
        """
        try:
            df = pd.DataFrame.from_dict(self.industry_data, orient='index')
            if file_path.endswith('.csv'):
                df.to_csv(file_path, encoding='utf-8-sig')
            elif file_path.endswith('.xlsx'):
                df.to_excel(file_path)
            else:
                return False
            return True
        except Exception as e:
            print(f"导出行业数据失败: {str(e)}")
            return False

    def get_eastmoney_board_data(self) -> Dict:
        """获取东方财富所有板块（指数/概念/行业/期货/外汇/商品等）数据"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            # 板块类型映射（可根据实际需求扩展）
            board_types = {
                "上证指数": "m:1+t:2",      # 上证指数
                "深证成指": "m:0+t:1",    # 深证成指
                "沪深300": "m:1+t:3",    # 沪深300
                "创业板": "m:0+t:13",     # 创业板
                "科创50": "m:1+t:23",     # 科创50
                "恒生指数": "m:100+t:1",  # 恒生指数
                "黄金": "m:105+t:1",      # 黄金
                "原油": "m:106+t:1",      # 原油
                "美元": "m:103+t:1",      # 美元
                # ...可继续扩展
            }
            result = {}
            for name, fs in board_types.items():
                params = {
                    "pn": "1",
                    "pz": "10",
                    "po": "1",
                    "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f13,f100,f103"
                }
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                        for item in data['data']['diff']:
                            code = item['f12']
                            board_name = item['f14']
                            result[name] = {
                                'code': code,
                                'name': board_name,
                                'last_price': item.get('f2'),
                                'chg': item.get('f4'),
                                'chg_pct': item.get('f3'),
                                'volume': item.get('f5'),
                                'amount': item.get('f6'),
                                'turnover': item.get('f8'),
                                'market': name
                            }
            self.log_manager.info(f"获取东方财富板块数据条数: {len(result)}")
            return result
        except Exception as e:
            self.log_manager.error(f"获取东方财富板块数据失败: {str(e)}")
            return {}

    def get_eastmoney_board_list(self, board_type='index'):
        """
        获取东方财富板块列表
        board_type: 'index'（指数）, 'industry'（行业）, 'concept'（概念）, 'area'（地区）
        """
        url_map = {
            'index': 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=b:MK0010,b:MK0021,b:MK0022,b:MK0023,b:MK0024,b:MK0025,b:MK0026,b:MK0027,b:MK0028,b:MK0029,b:MK0030,b:MK0031,b:MK0032,b:MK0033,b:MK0034,b:MK0035,b:MK0036,b:MK0037,b:MK0038,b:MK0039,b:MK0040,b:MK0041,b:MK0042,b:MK0043,b:MK0044,b:MK0045,b:MK0046,b:MK0047,b:MK0048,b:MK0049,b:MK0050&fields=f12,f14',
            'industry': 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2,m:90+t:3,m:90+t:4&fields=f12,f14',
            'concept': 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:1&fields=f12,f14',
            'area': 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:5&fields=f12,f14'
        }
        url = url_map.get(board_type)
        if not url:
            return []
        try:
            resp = requests.get(url)
            data = resp.json()
            if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                return [{'code': item['f12'], 'name': item['f14']} for item in data['data']['diff']]
        except Exception as e:
            self.log_manager.error(f"获取{board_type}板块失败: {e}")
        return []

    def get_eastmoney_board_members(self, board_code):
        """
        获取某板块成分股
        """
        url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=b:{board_code}&fields=f12,f14"
        try:
            resp = requests.get(url)
            data = resp.json()
            if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                return [{'code': item['f12'], 'name': item['f14']} for item in data['data']['diff']]
        except Exception as e:
            self.log_manager.error(f"获取板块成分股失败: {e}")
        return []

    def get_major_indices(self) -> Dict[str, dict]:
        """
        获取主流指数/板块数据（如上证指数、沪深300等）
        Returns:
            dict: {指数名称: {code, name, market, ...}}
        """
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            # 这里的fs参数可根据东财文档调整，包含主流指数
            params = {
                "pn": "1",
                "pz": "100",
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:1+t:2,m:1+t:23,m:1+t:24,m:1+t:25,m:1+t:26,m:1+t:27,m:1+t:28,m:1+t:29,m:1+t:30,m:1+t:31,m:1+t:32,m:1+t:33,m:1+t:34,m:1+t:35,m:1+t:36,m:1+t:37,m:1+t:38,m:1+t:39",  # 常见指数
                "fields": "f12,f14"
            }
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['rc'] == 0 and 'data' in data and 'diff' in data['data']:
                    result = {}
                    for item in data['data']['diff']:
                        code = item['f12']
                        name = item['f14']
                        result[name] = {
                            'code': code,
                            'name': name,
                            'market': 'INDEX'
                        }
                    self.log_manager.info(f"获取主流指数数据条数: {len(result)}")
                    return result
            return {}
        except Exception as e:
            self.log_manager.error(f"获取主流指数数据失败: {str(e)}")
            return {}
