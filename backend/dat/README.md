# dlib 人脸模型

项目使用 `face_recognition` 对 dlib 模型进行封装，运行时需要：

- `shape_predictor_68_face_landmarks.dat`
- `dlib_face_recognition_resnet_model_v1.dat`

模型由 `face_recognition_models` 包安装，不把大型 `.dat` 文件提交到 Git。

Windows 推荐使用 Python 3.10 CPU 环境：

```powershell
conda install --override-channels -c conda-forge dlib=19.24.6=cpu_py310h6715ef7_2 face_recognition
pip install -r requirements.txt
```

验证模型：

```powershell
python -c "import dlib, face_recognition_models as m; print(dlib.__version__); print(m.pose_predictor_model_location()); print(m.face_recognition_model_location())"
```
