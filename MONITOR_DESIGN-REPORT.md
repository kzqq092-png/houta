系统指标体系重构：详细开发计划与实施要点
本计划分为三个核心阶段，每个阶段包含一系列明确的任务。我们将严格遵循此计划，以确保架构的完美落地。
阶段一：构建强大的服务化后端（预计耗时：60%）
此阶段是整个项目地基，我们将构建出所有核心的、非UI的服务组件。
任务 1.1：搭建模块结构
操作：在 core/ 目录下创建新的子目录 metrics/。
操作：在 core/metrics/ 中创建以下文件：
__init__.py
events.py (用于定义指标事件)
resource_service.py (系统资源服务)
app_metrics_service.py (应用性能度量服务)
aggregation_service.py (指标聚合服务)
repository.py (数据库仓储)
注意细节：这个清晰的目录结构是代码高内聚性的物理体现，为后续开发打下良好基础。
任务 1.2：定义核心事件
文件：core/metrics/events.py
操作：
定义 SystemResourceUpdated 事件类，它应携带一个包含 cpu_percent, memory_percent, disk_percent 的数据载体（如 dataclass）。
定义 ApplicationMetricRecorded 事件类，它应携带 operation_name: str, duration: float, was_successful: bool 等关键信息。
注意细节：事件是模块间通信的契约。定义清晰、不可变的事件结构至关重要。
任务 1.3：实现数据库仓储 (MetricsRepository)
文件：core/metrics/repository.py
操作：
创建 MetricsRepository 类，负责所有 sqlite3 数据库操作。
在构造函数中连接至 db/metrics.db，并调用初始化方法。
实现 _initialize_schema() 方法，使用 CREATE TABLE IF NOT EXISTS 创建两张核心表：
resource_metrics_summary (t_stamp, cpu, mem, disk)
app_metrics_summary (t_stamp, operation, avg_duration, max_duration, call_count, error_count)
实现 save_aggregated_metrics_batch(data) 方法，使用 executemany 批量写入聚合后的数据。
实现 query_historical_data(...) 方法，用于UI查询历史趋势。
注意细节：
必须使用参数化查询（?占位符）来防止SQL注入。
所有数据库连接和游标操作都应使用 try...finally 确保资源被正确关闭。
表的初始化应是幂等的，即多次运行不会出错。
任务 1.4：实现三大核心服务
实现 SystemResourceService (resource_service.py):
创建一个后台 threading.Thread，在循环中用 psutil 采集数据。
通过 EventBus 发布 SystemResourceUpdated 事件。
注意细节：必须实现 dispose() 方法，该方法可以安全地停止并 join() 后台线程，防止程序退出时僵尸线程。监控间隔应从 ConfigService 读取，使其可配置。
实现 ApplicationMetricsService (app_metrics_service.py):
提供核心的 @measure_time(operation_name) 装饰器。
装饰器内部通过 try...except...finally 结构，精确记录耗时和成功状态，并发布 ApplicationMetricRecorded 事件。
注意细节：为了方便在项目中各处使用，可以提供一个全局的 get_app_metrics_service() 函数来获取服务单例。
实现 MetricsAggregationService (aggregation_service.py):
这是后端的核心。在初始化时，订阅 SystemResourceUpdated 和 ApplicationMetricRecorded 事件。
在内存中维护聚合数据结构（如 defaultdict）。
实现异步写入：启动一个 threading.Timer，周期性地（例如60秒）调用 _flush_buffer_to_db() 方法。
_flush_buffer_to_db() 方法将内存缓冲区的数据交给 MetricsRepository 进行批量写入。
注意细节：所有对内存聚合数据的读写操作都必须使用 threading.RLock 加以保护，以应对多线程环境下的数据竞争问题。
阶段二：重构现有代码，全面整合（预计耗时：20%）
此阶段的目标是"除旧迎新"，用我们的新服务替换掉所有旧的、冗余的实现。
任务 2.1：注册新服务
文件：main.py
操作：在应用的启动逻辑 _register_services 中，将我们创建的 MetricsRepository, SystemResourceService, ApplicationMetricsService, MetricsAggregationService 注册到全局的 ServiceContainer 中。
注意细节：注意服务的依赖关系和初始化顺序，确保被依赖的服务先被创建。
任务 2.2：清理冗余代码
操作：
果断删除 utils/performance_monitor.py 文件。
果断删除 monitor_chart_performance.py 文件。
在 optimization/optimization_dashboard.py 中，删除其内部的 SystemMonitor 线程类。
在 analysis/system_health_checker.py 中，删除所有直接使用 psutil 的方法。
注意细节：删除文件后，需要通过全局搜索确保没有任何地方还在 import 它们，彻底根除依赖。
任务 2.3：应用新服务
重构 SystemHealthChecker: 让它从服务容器获取 MetricsAggregationService，并直接查询聚合数据来完成健康评估。
应用装饰器：在关键业务逻辑处（如 ChartWidget.update_chart, EnhancedPatternRecognizer.identify_patterns），应用 @measure_time(...) 装饰器。
阶段三：UI赋能与价值呈现（预计耗时：20%）
这是将我们的后端能力转化为用户价值的最后一步。
任务 3.1：创建 PerformanceDashboardPanel
文件：gui/panels/performance_dashboard_panel.py
操作：创建新的UI面板类，并在主窗口（如 main_window_coordinator.py）中添加加载和显示此面板的逻辑。
注意细节：设计为可停靠（dockable）或可关闭的面板，不干扰用户的主要工作流程。
任务 3.2：实现仪表盘功能
实时状态：
UI面板订阅 SystemResourceUpdated 事件。
注意细节：事件处理函数必须通过 Qt的信号/槽机制 来更新UI，这是跨线程UI操作的唯一安全方式。例如，EventBus 在收到事件后，可以发射一个 pyqtSignal，由UI面板的槽函数连接。
性能排行与历史趋势：
为UI上的"查询/刷新"按钮绑定事件。
注意细节：按钮的槽函数不应直接调用可能耗时的数据库查询。它应该启动一个 QThread 工作线程来执行 MetricsRepository 的查询，查询结束后再通过信号将结果发回主线程更新UI。这能确保即使用户查询一周的数据，UI界面也绝不卡顿。

阶段四：系统集成、调试与稳定化
在完成核心功能开发后，我们进行了全面的集成测试，并在此过程中发现和解决了一系列深层次的问题。这些修复是确保系统稳定可靠的关键。

问题 1：模块导入失败 (ModuleNotFoundError)
现象: unittest 无法找到 test.test_integration_monitoring 模块。
根因: test/ 目录下缺少 __init__.py 文件，导致 Python 无法将其识别为一个可导入的包。
解决: 在 test/ 目录下创建了一个空的 __init__.py 文件，解决了模块的发现问题。

问题 2：事件对象属性缺失 (AttributeError)
现象: EventBus 在发布事件时，因找不到 event.event_type 属性而崩溃。
根因: 基于 dataclass 的新事件（如 ApplicationMetricRecorded）没有 event_type 实例属性，而旧版 EventBus 依赖此属性。
解决: 为所有 dataclass 事件添加了 event_type: ClassVar[str] 类属性，确保 EventBus 能识别它们。

问题 3：事件系统架构不兼容
现象: 即便解决了 AttributeError，EventBus 仍然无法正确分发事件。
根因: EventBus 的 subscribe 方法期望接收一个字符串作为事件类型，而新的服务化代码传递的是事件类本身。这是一个根本性的设计冲突。
解决: 对 EventBus 进行了核心重构。subscribe 和 publish 方法现在都基于事件的类型 (type) 来工作，使其与 dataclass 事件系统完全兼容。

问题 4：数据库无数据 (AssertionError)
现象: 集成测试断言失败，因为数据库中没有写入任何资源指标。
根因: MetricsAggregationService 的 dispose 方法在执行最终刷新后，会错误地再次调度一个新的刷新定时器，导致数据丢失或未被及时写入。
解决: 重构了 dispose 和 _flush_buffer_to_db 方法，分离了数据库写入和定时器调度的逻辑，确保了服务在停止时能正确、且仅执行一次最终的数据刷新。

最终成果
经过上述修复，整个监控系统的后端服务已完全稳定。集成测试（test_integration_monitoring.py）现已能稳定通过，证明了从数据采集、事件分发、数据聚合到最终数据库写入的整个流程是正确且可靠的。