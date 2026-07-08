# dlib face models

The project uses `face_recognition` (wrapper around dlib). Runtime requires:

- `shape_predictor_68_face_landmarks.dat`
- `dlib_face_recognition_resnet_model_v1.dat`

These are installed by the `face-recognition-models` pip package and are **not committed to Git**.

## Environment setup

See [docs/DEV_SETUP.md](../../docs/DEV_SETUP.md) and [backend/README.md](../README.md).

Verify model paths:

```powershell
conda activate home-camera
python -c "import dlib, face_recognition_models as m; print(dlib.__version__); print(m.pose_predictor_model_location()); print(m.face_recognition_model_location())"
```
