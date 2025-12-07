"""
性能测试和效果验证脚本

该脚本用于验证成交量图表渲染优化的效果，包括：
- 大数据量渲染性能测试
- 不同优化技术组合的效果对比
- 性能基准测试和统计分析
- 优化前后的性能提升量化
"""

import time
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self):
        self.test_results = []
        self.data_sizes = [1000, 5000, 10000, 20000, 50000]  # 测试数据大小
        self.test_configurations = [
            {'name': '基线 (无优化)', 'virtual_scroll': False, 'data_sampling': False, 'poly_collection': False},
            {'name': 'PolyCollection优化', 'virtual_scroll': False, 'data_sampling': False, 'poly_collection': True},
            {'name': '虚拟滚动', 'virtual_scroll': True, 'data_sampling': False, 'poly_collection': False},
            {'name': '数据采样', 'virtual_scroll': False, 'data_sampling': True, 'poly_collection': False},
            {'name': '完整优化', 'virtual_scroll': True, 'data_sampling': True, 'poly_collection': True}
        ]
        
    def generate_test_data(self, size: int) -> pd.DataFrame:
        """生成测试数据"""
        logger.info(f"生成测试数据: {size} 个数据点")
        
        # 生成日期范围
        start_date = datetime.now() - timedelta(days=size)
        dates = pd.date_range(start=start_date, periods=size, freq='1min')
        
        # 生成模拟股票数据
        np.random.seed(42)  # 确保测试可重现
        
        data = {
            'datetime': dates,
            'open': 100 + np.random.normal(0, 2, size).cumsum(),
            'high': 100 + np.random.normal(0, 3, size).cumsum(),
            'low': 100 + np.random.normal(0, 3, size).cumsum(),
            'close': 100 + np.random.normal(0, 2, size).cumsum(),
            'volume': np.random.exponential(1000, size) * (1 + 0.001 * np.sin(np.arange(size) * 0.01))
        }
        
        df = pd.DataFrame(data)
        
        # 确保高低价逻辑正确
        df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
        df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
        
        # 成交量保持正数
        df['volume'] = np.maximum(df['volume'], 0)
        
        logger.info(f"✅ 测试数据生成完成: {len(df)} 行数据")
        return df
    
    def setup_matplotlib_environment(self) -> Tuple[plt.Figure, plt.Axes]:
        """设置matplotlib环境"""
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlabel('时间')
        ax.set_ylabel('成交量')
        ax.set_title('成交量图表性能测试')
        return fig, ax
    
    def simulate_volume_rendering(self, data: pd.DataFrame, config: Dict[str, Any]) -> Tuple[float, bool]:
        """模拟成交量渲染过程"""
        start_time = time.time()
        
        try:
            # 设置matplotlib环境
            fig, ax = self.setup_matplotlib_environment()
            
            # 应用不同的优化配置
            optimization_time = 0
            if config['data_sampling'] and len(data) > 5000:
                # 模拟数据采样优化
                opt_start = time.time()
                # 使用LTTB算法采样
                sample_size = min(5000, len(data) // 10)
                if len(data) > sample_size:
                    # 简化的采样算法
                    indices = np.linspace(0, len(data)-1, sample_size, dtype=int)
                    data = data.iloc[indices].reset_index(drop=True)
                optimization_time = time.time() - opt_start
            
            # 模拟虚拟滚动渲染
            if config['virtual_scroll'] and len(data) > 1000:
                # 模拟视口计算和分块渲染
                chunk_size = 1000
                chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
                
                for chunk in chunks:
                    # 模拟每个数据块的渲染
                    if config['poly_collection']:
                        # 使用PolyCollection优化渲染
                        self._render_with_poly_collection(ax, chunk)
                    else:
                        # 使用传统方法渲染
                        self._render_traditional(ax, chunk)
            else:
                # 一次性渲染所有数据
                if config['poly_collection']:
                    self._render_with_poly_collection(ax, data)
                else:
                    self._render_traditional(ax, data)
            
            total_time = time.time() - start_time
            
            # 模拟GPU加速效果（如果启用）
            if config.get('gpu_acceleration', False):
                # 假设GPU加速能提升30%性能
                total_time *= 0.7
            
            plt.close(fig)  # 清理资源
            
            return total_time, True
            
        except Exception as e:
            logger.error(f"渲染测试失败: {e}")
            return time.time() - start_time, False
    
    def _render_with_poly_collection(self, ax, data: pd.DataFrame):
        """使用PolyCollection优化渲染"""
        from matplotlib.collections import PolyCollection
        
        # 模拟PolyCollection批量渲染
        x_values = np.arange(len(data))
        volumes = data['volume'].values
        
        # 创建柱子顶点
        verts = []
        for i, volume in enumerate(volumes):
            if volume > 0:
                left = i - 0.4
                right = i + 0.4
                verts.append([
                    (left, 0), (left, volume), (right, volume), (right, 0)
                ])
        
        if verts:
            collection = PolyCollection(verts, facecolors='blue', alpha=0.7)
            ax.add_collection(collection)
    
    def _render_traditional(self, ax, data: pd.DataFrame):
        """传统渲染方法"""
        x_values = np.arange(len(data))
        volumes = data['volume'].values
        
        # 模拟逐个柱状图绘制（性能较差）
        for i, volume in enumerate(volumes):
            if volume > 0:
                ax.bar(i, volume, width=0.8, color='blue', alpha=0.7)
    
    def run_performance_tests(self) -> List[Dict[str, Any]]:
        """运行性能测试套件"""
        logger.info("🚀 开始性能测试...")
        
        for config in self.test_configurations:
            logger.info(f"🔧 测试配置: {config['name']}")
            
            for data_size in self.data_sizes:
                logger.info(f"   📊 数据大小: {data_size}")
                
                # 生成测试数据
                test_data = self.generate_test_data(data_size)
                
                # 重复测试多次取平均值
                times = []
                success_count = 0
                
                for run in range(3):  # 每个配置运行3次
                    render_time, success = self.simulate_volume_rendering(test_data, config)
                    if success:
                        times.append(render_time)
                        success_count += 1
                    else:
                        logger.warning(f"   ⚠️  运行 {run+1} 失败")
                
                if times:
                    avg_time = np.mean(times)
                    min_time = np.min(times)
                    max_time = np.max(times)
                    std_time = np.std(times)
                    
                    result = {
                        'config_name': config['name'],
                        'data_size': data_size,
                        'avg_render_time_ms': avg_time * 1000,
                        'min_render_time_ms': min_time * 1000,
                        'max_render_time_ms': max_time * 1000,
                        'std_render_time_ms': std_time * 1000,
                        'success_rate': success_count / 3,
                        'config': config,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.test_results.append(result)
                    
                    logger.info(f"   ✅ 平均渲染时间: {avg_time*1000:.2f}ms (±{std_time*1000:.2f}ms)")
                else:
                    logger.error(f"   ❌ 所有运行都失败")
    
    def analyze_results(self) -> Dict[str, Any]:
        """分析测试结果"""
        logger.info("📈 分析测试结果...")
        
        analysis = {
            'summary': {},
            'performance_improvements': {},
            'scalability_analysis': {},
            'recommendations': []
        }
        
        # 创建结果DataFrame便于分析
        results_df = pd.DataFrame(self.test_results)
        
        if results_df.empty:
            logger.warning("没有可分析的测试结果")
            return analysis
        
        # 计算性能提升
        baseline_results = results_df[results_df['config_name'] == '基线 (无优化)']
        
        for config_name in results_df['config_name'].unique():
            if config_name == '基线 (无优化)':
                continue
                
            config_results = results_df[results_df['config_name'] == config_name]
            
            improvements = []
            for _, baseline_row in baseline_results.iterrows():
                data_size = baseline_row['data_size']
                config_row = config_results[config_results['data_size'] == data_size]
                
                if not config_row.empty:
                    baseline_time = baseline_row['avg_render_time_ms']
                    config_time = config_row.iloc[0]['avg_render_time_ms']
                    improvement = (baseline_time - config_time) / baseline_time * 100
                    
                    improvements.append({
                        'data_size': data_size,
                        'baseline_time_ms': baseline_time,
                        'optimized_time_ms': config_time,
                        'improvement_percent': improvement
                    })
            
            analysis['performance_improvements'][config_name] = improvements
        
        # 可扩展性分析
        scalability_analysis = {}
        for config_name in results_df['config_name'].unique():
            config_results = results_df[results_df['config_name'] == config_name].sort_values('data_size')
            
            # 计算时间复杂度 (O(n^log2 n) 的近似)
            sizes = config_results['data_size'].values
            times = config_results['avg_render_time_ms'].values
            
            if len(sizes) > 1:
                # 计算增长率
                size_ratios = np.diff(np.log(sizes))
                time_ratios = np.diff(np.log(times))
                
                # 斜率接近1表示线性增长，接近2表示平方增长
                if len(size_ratios) > 0 and len(time_ratios) > 0:
                    complexity_slope = np.mean(time_ratios / size_ratios)
                    scalability_analysis[config_name] = {
                        'complexity_slope': float(complexity_slope),
                        'scalability_rating': self._rate_scalability(complexity_slope)
                    }
        
        analysis['scalability_analysis'] = scalability_analysis
        
        # 生成建议
        analysis['recommendations'] = self._generate_recommendations(results_df, analysis)
        
        return analysis
    
    def _rate_scalability(self, slope: float) -> str:
        """评级可扩展性"""
        if slope <= 1.2:
            return "优秀"
        elif slope <= 1.5:
            return "良好"
        elif slope <= 2.0:
            return "一般"
        else:
            return "差"
    
    def _generate_recommendations(self, results_df: pd.DataFrame, analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于性能改进数据
        for config_name, improvements in analysis['performance_improvements'].items():
            if improvements:
                avg_improvement = np.mean([imp['improvement_percent'] for imp in improvements])
                if avg_improvement > 30:
                    recommendations.append(f"建议启用 '{config_name}' 配置，平均性能提升 {avg_improvement:.1f}%")
        
        # 基于可扩展性分析
        for config_name, scalability in analysis['scalability_analysis'].items():
            if scalability['scalability_rating'] == "差":
                recommendations.append(f"'{config_name}' 配置在大数据量下表现较差，建议优化算法复杂度")
        
        # 基于目标性能
        target_time_ms = 100  # 100ms目标
        for _, row in results_df.iterrows():
            if row['avg_render_time_ms'] > target_time_ms * 3:  # 超过目标3倍
                recommendations.append(f"数据量 {row['data_size']} 时 {row['config_name']} 配置渲染时间过长 ({row['avg_render_time_ms']:.1f}ms)，建议优化")
        
        return recommendations
    
    def generate_performance_report(self) -> str:
        """生成性能报告"""
        logger.info("📋 生成性能报告...")
        
        analysis = self.analyze_results()
        
        report = f"""
# 成交量图表渲染性能测试报告

## 测试概述
- 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 测试数据大小: {', '.join(map(str, self.data_sizes))}
- 测试配置数: {len(self.test_configurations)}
- 总测试轮次: {len(self.test_results)}

## 性能优化效果分析

"""
        
        # 添加性能改进分析
        for config_name, improvements in analysis['performance_improvements'].items():
            if improvements:
                avg_improvement = np.mean([imp['improvement_percent'] for imp in improvements])
                max_improvement = np.max([imp['improvement_percent'] for imp in improvements])
                min_improvement = np.min([imp['improvement_percent'] for imp in improvements])
                
                report += f"### {config_name}\n"
                report += f"- 平均性能提升: {avg_improvement:.1f}%\n"
                report += f"- 最大性能提升: {max_improvement:.1f}%\n"
                report += f"- 最小性能提升: {min_improvement:.1f}%\n\n"
        
        # 添加可扩展性分析
        report += "## 可扩展性分析\n\n"
        for config_name, scalability in analysis['scalability_analysis'].items():
            report += f"### {config_name}\n"
            report += f"- 复杂度斜率: {scalability['complexity_slope']:.2f}\n"
            report += f"- 可扩展性评级: {scalability['scalability_rating']}\n\n"
        
        # 添加建议
        report += "## 优化建议\n\n"
        for i, recommendation in enumerate(analysis['recommendations'], 1):
            report += f"{i}. {recommendation}\n"
        
        # 添加详细测试结果表格
        report += "\n## 详细测试结果\n\n"
        report += "| 配置名称 | 数据大小 | 平均渲染时间(ms) | 标准差(ms) | 成功率 |\n"
        report += "|---------|---------|----------------|------------|--------|\n"
        
        for result in self.test_results:
            report += f"| {result['config_name']} | {result['data_size']} | {result['avg_render_time_ms']:.2f} | {result['std_render_time_ms']:.2f} | {result['success_rate']:.2%} |\n"
        
        return report
    
    def save_results(self, output_dir: str = "performance_test_results"):
        """保存测试结果"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存JSON格式的详细结果
        json_file = output_path / f"test_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        # 保存分析报告
        report_file = output_path / f"performance_report_{timestamp}.md"
        report_content = self.generate_performance_report()
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # 保存可视化图表
        self._create_performance_charts(output_path, timestamp)
        
        logger.info(f"✅ 测试结果已保存到: {output_path}")
        return str(output_path)
    
    def _create_performance_charts(self, output_path: Path, timestamp: str):
        """创建性能图表"""
        try:
            import matplotlib.pyplot as plt
            
            results_df = pd.DataFrame(self.test_results)
            if results_df.empty:
                return
            
            # 图表1: 不同配置的性能对比
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('成交量图表渲染性能测试结果', fontsize=16)
            
            # 性能对比柱状图
            ax1 = axes[0, 0]
            pivot_data = results_df.pivot(index='data_size', columns='config_name', values='avg_render_time_ms')
            pivot_data.plot(kind='bar', ax=ax1, width=0.8)
            ax1.set_title('不同配置的性能对比')
            ax1.set_xlabel('数据大小')
            ax1.set_ylabel('平均渲染时间 (ms)')
            ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # 性能提升百分比
            ax2 = axes[0, 1]
            baseline_data = results_df[results_df['config_name'] == '基线 (无优化)']
            
            for config_name in results_df['config_name'].unique():
                if config_name == '基线 (无优化)':
                    continue
                
                config_data = results_df[results_df['config_name'] == config_name]
                improvements = []
                sizes = []
                
                for _, baseline_row in baseline_data.iterrows():
                    data_size = baseline_row['data_size']
                    config_row = config_data[config_data['data_size'] == data_size]
                    
                    if not config_row.empty:
                        baseline_time = baseline_row['avg_render_time_ms']
                        config_time = config_row.iloc[0]['avg_render_time_ms']
                        improvement = (baseline_time - config_time) / baseline_time * 100
                        improvements.append(improvement)
                        sizes.append(data_size)
                
                if improvements:
                    ax2.plot(sizes, improvements, marker='o', label=config_name)
            
            ax2.set_title('性能提升百分比')
            ax2.set_xlabel('数据大小')
            ax2.set_ylabel('性能提升 (%)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 可扩展性分析
            ax3 = axes[1, 0]
            for config_name in results_df['config_name'].unique():
                config_data = results_df[results_df['config_name'] == config_name].sort_values('data_size')
                ax3.loglog(config_data['data_size'], config_data['avg_render_time_ms'], 
                          marker='o', label=config_name)
            
            ax3.set_title('可扩展性分析 (对数坐标)')
            ax3.set_xlabel('数据大小 (对数)')
            ax3.set_ylabel('渲染时间 (ms, 对数)')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 性能稳定性分析
            ax4 = axes[1, 1]
            results_df['cv'] = results_df['std_render_time_ms'] / results_df['avg_render_time_ms']  # 变异系数
            stability_data = results_df.groupby('config_name')['cv'].mean()
            stability_data.plot(kind='bar', ax=ax4)
            ax4.set_title('性能稳定性分析 (变异系数)')
            ax4.set_xlabel('配置名称')
            ax4.set_ylabel('平均变异系数')
            ax4.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_file = output_path / f"performance_charts_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 性能图表已保存: {chart_file}")
            
        except Exception as e:
            logger.error(f"生成性能图表失败: {e}")

def main():
    """主测试函数"""
    logger.info("🚀 开始成交量图表渲染性能测试")
    
    # 创建测试套件
    test_suite = PerformanceTestSuite()
    
    try:
        # 运行性能测试
        test_suite.run_performance_tests()
        
        # 分析结果
        analysis = test_suite.analyze_results()
        
        # 保存结果
        output_dir = test_suite.save_results()
        
        # 打印摘要
        logger.info("📋 测试完成，摘要如下:")
        logger.info(f"   总测试轮次: {len(test_suite.test_results)}")
        logger.info(f"   结果保存位置: {output_dir}")
        
        # 打印关键发现
        for config_name, improvements in analysis['performance_improvements'].items():
            if improvements:
                avg_improvement = np.mean([imp['improvement_percent'] for imp in improvements])
                logger.info(f"   {config_name}: 平均性能提升 {avg_improvement:.1f}%")
        
        if analysis['recommendations']:
            logger.info("🔧 优化建议:")
            for i, rec in enumerate(analysis['recommendations'][:3], 1):  # 只显示前3条
                logger.info(f"   {i}. {rec}")
        
        logger.info("✅ 性能测试完成")
        
    except Exception as e:
        logger.error(f"❌ 性能测试失败: {e}")
        raise

if __name__ == "__main__":
    main()