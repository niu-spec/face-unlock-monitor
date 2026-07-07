# 人脸识别模型

本项目通过 `face_recognition_models` Python 包提供 dlib 模型，不把大型
`.dat` 文件提交到 Git：

- `shape_predictor_68_face_landmarks.dat`
- `dlib_face_recognition_resnet_model_v1.dat`

安装项目环境后可运行以下命令确认模型路径：

```powershell
python -c "import face_recognition_models as m; print(m.pose_predictor_model_location()); print(m.face_recognition_model_location())"
```

运行代码时由 `face_recognition` 自动加载这些模型，无需手动指定路径。
