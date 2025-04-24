import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

TENSORFLOW_AVAILABLE = False
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout, LSTM, GRU, Bidirectional, Conv1D, MaxPooling1D, Flatten
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    print("TensorFlow/Keras 未安装，无法使用深度学习模型")

def build_deep_learning_model(X_train, y_train, X_test, y_test, model_type='lstm', sequence_length=20, batch_size=32, epochs=50):
    """
    构建并训练深度学习模型
    
    参数:
        X_train: 训练特征数据
        y_train: 训练标签数据
        X_test: 测试特征数据
        y_test: 测试标签数据
        model_type: 模型类型 ('lstm', 'gru', 'cnn', 'mlp')
        sequence_length: 时间序列长度（仅用于RNN模型）
        batch_size: 批次大小
        epochs: 训练轮数
    
    返回:
        model: 训练好的模型
        history: 训练历史
    """
    if not TENSORFLOW_AVAILABLE:
        print("无法构建深度学习模型：TensorFlow/Keras 未安装")
        return None, None
    
    # 设置随机种子以确保可重复性
    tf.random.set_seed(42)
    np.random.seed(42)
    
    # 确保输入数据是NumPy数组
    def ensure_numpy_array(data):
        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series):
            return data.values
        return data
    
    X_train = ensure_numpy_array(X_train)
    y_train = ensure_numpy_array(y_train)
    X_test = ensure_numpy_array(X_test)
    y_test = ensure_numpy_array(y_test)
    
    # 获取特征数量
    n_features = X_train.shape[1]
    
    # 创建类别编码的y
    # 对于三分类问题：-1, 0, 1 -> 0, 1, 2
    y_train_encoded = y_train.copy()
    y_test_encoded = y_test.copy()
    
    # 将-1转换为0，0转换为1，1转换为2
    y_train_encoded[y_train_encoded == -1] = 0
    y_train_encoded[y_train_encoded == 0] = 1
    y_train_encoded[y_train_encoded == 1] = 2
    y_test_encoded[y_test_encoded == -1] = 0
    y_test_encoded[y_test_encoded == 0] = 1
    y_test_encoded[y_test_encoded == 1] = 2
    
    # 转换为one-hot编码
    y_train_categorical = tf.keras.utils.to_categorical(y_train_encoded, num_classes=3)
    y_test_categorical = tf.keras.utils.to_categorical(y_test_encoded, num_classes=3)
    
    # 根据模型类型重塑数据
    if model_type in ['lstm', 'gru']:
        # 为RNN模型准备序列数据
        def reshape_to_sequences(X, seq_length):
            # 确保我们有足够的数据来创建序列
            if len(X) < seq_length:
                raise ValueError(f"数据长度 {len(X)} 小于序列长度 {seq_length}")
            
            # 创建序列
            sequences = []
            for i in range(len(X) - seq_length + 1):
                sequences.append(X[i:i+seq_length])
            
            return np.array(sequences)
        
        # 转换训练集和测试集
        try:
            X_train_seq = reshape_to_sequences(X_train, sequence_length)
            X_test_seq = reshape_to_sequences(X_test, sequence_length)
            
            # 对应的标签应该是每个序列的最后一天的标签
            y_train_seq = y_train_categorical[sequence_length-1:]
            y_test_seq = y_test_categorical[sequence_length-1:]
            
            X_train = X_train_seq
            X_test = X_test_seq
            y_train_categorical = y_train_seq
            y_test_categorical = y_test_seq
            
            # 更新特征维度
            n_features = X_train.shape[2]
            
            print(f"序列化后的数据形状: X_train={X_train.shape}, y_train={y_train_categorical.shape}")
        except ValueError as e:
            print(f"无法创建序列: {e}")
            model_type = 'mlp'  # 回退到MLP模型
    elif model_type == 'cnn':
        # 为CNN模型重塑数据（添加通道维度）
        X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
        X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))
        print(f"CNN数据形状: X_train={X_train.shape}, y_train={y_train_categorical.shape}")
    
    # 构建模型
    model = Sequential()
    
    if model_type == 'lstm':
        # LSTM模型
        model.add(LSTM(100, input_shape=(sequence_length, n_features), return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(50))
        model.add(Dropout(0.2))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(3, activation='softmax'))  # 三分类输出
    elif model_type == 'gru':
        # GRU模型
        model.add(GRU(100, input_shape=(sequence_length, n_features), return_sequences=True))
        model.add(Dropout(0.2))
        model.add(GRU(50))
        model.add(Dropout(0.2))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(3, activation='softmax'))  # 三分类输出
    elif model_type == 'cnn':
        # CNN模型
        model.add(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(n_features, 1)))
        model.add(MaxPooling1D(pool_size=2))
        model.add(Conv1D(filters=32, kernel_size=3, activation='relu'))
        model.add(MaxPooling1D(pool_size=2))
        model.add(Flatten())
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(3, activation='softmax'))  # 三分类输出
    else:  # 默认为MLP
        # 多层感知机模型
        model.add(Dense(128, activation='relu', input_dim=n_features))
        model.add(Dropout(0.3))
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(3, activation='softmax'))  # 三分类输出
    
    # 编译模型
    model.compile(
        loss='categorical_crossentropy',
        optimizer=Adam(learning_rate=0.001),
        metrics=['accuracy']
    )
    
    # 输出模型摘要
    model.summary()
    
    # 设置回调函数
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=0.0001),
        ModelCheckpoint('best_model.h5', monitor='val_accuracy', save_best_only=True, verbose=1)
    ]
    
    # 训练模型
    try:
        history = model.fit(
            X_train, y_train_categorical,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test_categorical),
            callbacks=callbacks,
            verbose=1
        )
        
        # 评估模型
        loss, accuracy = model.evaluate(X_test, y_test_categorical, verbose=0)
        print(f"测试损失: {loss:.4f}")
        print(f"测试准确率: {accuracy:.4f}")
        
        # 绘制训练历史
        plt.figure(figsize=(12, 5))
        
        # 绘制准确率
        plt.subplot(1, 2, 1)
        plt.plot(history.history['accuracy'], label='训练准确率')
        plt.plot(history.history['val_accuracy'], label='验证准确率')
        plt.title('模型准确率')
        plt.xlabel('轮次')
        plt.ylabel('准确率')
        plt.legend()
        
        # 绘制损失
        plt.subplot(1, 2, 2)
        plt.plot(history.history['loss'], label='训练损失')
        plt.plot(history.history['val_loss'], label='验证损失')
        plt.title('模型损失')
        plt.xlabel('轮次')
        plt.ylabel('损失')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('deep_learning_history.png', dpi=300)
        
        return model, history
    
    except Exception as e:
        print(f"训练过程出错: {e}")
        return None, None