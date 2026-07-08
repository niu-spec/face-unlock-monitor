"""Verify backend AI dependencies after conda setup."""
import sys


def main() -> int:
    import dlib
    import django
    import face_recognition

    print("dlib", dlib.__version__)
    print("face_recognition OK")
    print("django", django.get_version())
    return 0


if __name__ == "__main__":
    sys.exit(main())
