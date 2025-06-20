import os
import os.path as osp
import sys
import base64
import tempfile
import subprocess
from PIL import Image
from io import BytesIO
import requests

# LivePortrait imports (현재 디렉토리에서 LivePortrait-main까지의 경로 추가)
current_dir = os.path.dirname(os.path.abspath(__file__))
liveportrait_path = os.path.join(current_dir, "LivePortrait-main")
if liveportrait_path not in sys.path:
    sys.path.insert(0, liveportrait_path)

from src.config.argument_config import ArgumentConfig
from src.config.inference_config import InferenceConfig
from src.config.crop_config import CropConfig
from src.live_portrait_pipeline import LivePortraitPipeline


class FastLivePortraitPipeline(LivePortraitPipeline):
    """concat 처리를 생략한 빠른 LivePortrait 파이프라인"""
    
    def __init__(self, inference_cfg, crop_cfg, disable_concat=True):
        super().__init__(inference_cfg, crop_cfg)
        self.disable_concat = disable_concat
    
    def execute(self, args):
        """원본 execute를 호출하되, concat 처리를 조건부로 스킵"""
        # 일시적으로 concat을 비활성화하기 위한 monkey patching
        if self.disable_concat:
            # concat_frames 함수를 임시로 무력화
            import src.utils.video as video_utils
            original_concat_frames = video_utils.concat_frames
            
            def dummy_concat_frames(driving_image_lst, source_image_lst, I_p_lst):
                """concat을 생략하고 결과만 반환"""
                print("⚡ concat 처리 생략됨 (속도 최적화)")
                return I_p_lst  # 결과 프레임만 반환
            
            # 일시적으로 concat_frames 교체
            video_utils.concat_frames = dummy_concat_frames
            
            try:
                # 원본 execute 실행
                result = super().execute(args)
                return result
            finally:
                # 원본 함수 복원
                video_utils.concat_frames = original_concat_frames
        else:
            # concat 활성화된 경우 원본 그대로 실행
            return super().execute(args)


def partial_fields(target_class, kwargs):
    """ArgumentConfig에서 특정 클래스에 필요한 필드만 추출"""
    return target_class(**{k: v for k, v in kwargs.items() if hasattr(target_class, k)})


def fast_check_ffmpeg():
    """FFmpeg 설치 확인"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False


class LivePortraitConverter:
    """LivePortrait를 사용한 이미지-영상 변환 클래스"""
    
    def __init__(self):
        """컨버터 초기화"""
        print("LivePortraitConverter 초기화 중...")
        
        # FFmpeg 경로 설정
        ffmpeg_dir = os.path.join(os.getcwd(), "ffmpeg")
        if osp.exists(ffmpeg_dir):
            os.environ["PATH"] += (os.pathsep + ffmpeg_dir)
        
        # FFmpeg 확인
        if not fast_check_ffmpeg():
            raise ImportError(
                "FFmpeg is not installed. Please install FFmpeg (including ffmpeg and ffprobe) before running this script. https://ffmpeg.org/download.html"
            )
        
        print("LivePortraitConverter 초기화 완료")
    
    def convert_image_video_to_video(self, 
                                   source_image_path, 
                                   driving_video_path,
                                   output_dir=None,
                                   **kwargs):
        """
        이미지와 드라이빙 영상을 받아서 LivePortrait 영상 생성
        
        Args:
            source_image_path: 소스 이미지 파일 경로
            driving_video_path: 드라이빙 영상 파일 경로
            output_dir: 출력 디렉토리 (기본값: 임시 디렉토리)
            **kwargs: 추가 설정 옵션들
            
        Returns:
            str: 생성된 비디오 파일 경로
        """
        
        print(f"LivePortrait 변환 시작:")
        print(f"  - 소스 이미지: {source_image_path}")
        print(f"  - 드라이빙 영상: {driving_video_path}")
        
        # 파일 존재 확인
        if not osp.exists(source_image_path):
            raise FileNotFoundError(f"source info not found: {source_image_path}")
        if not osp.exists(driving_video_path):
            raise FileNotFoundError(f"driving info not found: {driving_video_path}")
        
        # 출력 디렉토리 설정
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        os.makedirs(output_dir, exist_ok=True)
        
        # ArgumentConfig 생성 (inference.py와 동일한 방식)
        args_dict = {
            'source': source_image_path,
            'driving': driving_video_path,
            'output_dir': output_dir,
            
            # 기본 inference 설정
            'flag_use_half_precision': kwargs.get('flag_use_half_precision', True),
            'flag_crop_driving_video': kwargs.get('flag_crop_driving_video', False),
            'device_id': kwargs.get('device_id', 0),
            'flag_force_cpu': kwargs.get('flag_force_cpu', False),
            'flag_normalize_lip': kwargs.get('flag_normalize_lip', False),
            'flag_source_video_eye_retargeting': kwargs.get('flag_source_video_eye_retargeting', False),
            'flag_eye_retargeting': kwargs.get('flag_eye_retargeting', False),
            'flag_lip_retargeting': kwargs.get('flag_lip_retargeting', False),
            'flag_stitching': kwargs.get('flag_stitching', True),
            'flag_relative_motion': kwargs.get('flag_relative_motion', True),
            'flag_pasteback': kwargs.get('flag_pasteback', True),
            'flag_do_crop': kwargs.get('flag_do_crop', True),
            'driving_option': kwargs.get('driving_option', "expression-friendly"),
            'driving_multiplier': kwargs.get('driving_multiplier', 1.0),
            'driving_smooth_observation_variance': kwargs.get('driving_smooth_observation_variance', 3e-7),
            'audio_priority': kwargs.get('audio_priority', 'driving'),
            'animation_region': kwargs.get('animation_region', "all"),
            
            # crop 설정
            'det_thresh': kwargs.get('det_thresh', 0.15),
            'scale': kwargs.get('scale', 2.3),
            'vx_ratio': kwargs.get('vx_ratio', 0),
            'vy_ratio': kwargs.get('vy_ratio', -0.125),
            'flag_do_rot': kwargs.get('flag_do_rot', True),
            'source_max_dim': kwargs.get('source_max_dim', 1280),
            'source_division': kwargs.get('source_division', 2),
            'scale_crop_driving_video': kwargs.get('scale_crop_driving_video', 2.2),
            'vx_ratio_crop_driving_video': kwargs.get('vx_ratio_crop_driving_video', 0.0),
            'vy_ratio_crop_driving_video': kwargs.get('vy_ratio_crop_driving_video', -0.1),
        }
        
        # ArgumentConfig 객체 생성
        args = ArgumentConfig(**args_dict)
        
        print(f"  - 출력 디렉토리: {args.output_dir}")
        
        try:
            # inference configs 생성 (inference.py와 동일)
            inference_cfg = partial_fields(InferenceConfig, args.__dict__)
            crop_cfg = partial_fields(CropConfig, args.__dict__)
            
            # FastLivePortraitPipeline 생성 및 실행 (concat 최적화)
            save_concat = kwargs.get('flag_save_concat_video', False)
            print(f"LivePortraitPipeline 초기화 중... (concat: {'활성화' if save_concat else '비활성화'})")
            
            live_portrait_pipeline = FastLivePortraitPipeline(
                inference_cfg=inference_cfg,
                crop_cfg=crop_cfg,
                disable_concat=not save_concat  # concat 비활성화로 속도 향상
            )
            
            print("LivePortrait 실행 중...")
            live_portrait_pipeline.execute(args)
            
            # 결과 파일 경로 찾기 (일반적으로 output_dir에 생성됨)
            output_files = [f for f in os.listdir(output_dir) if f.endswith(('.mp4', '.avi', '.mov'))]
            if not output_files:
                raise RuntimeError("출력 영상 파일을 찾을 수 없습니다.")
            
            output_path = os.path.join(output_dir, output_files[0])
            print(f"LivePortrait 변환 완료: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"LivePortrait 변환 중 오류: {str(e)}")
            raise e


def load_image_from_input(image_input):
    """
    Base64 인코딩된 문자열이나 URL에서 이미지를 로드하고 임시 파일로 저장
    
    Args:
        image_input: Base64 문자열 또는 이미지 URL
        
    Returns:
        str: 저장된 이미지 파일 경로
    """
    
    if not image_input:
        raise ValueError("이미지 입력이 없습니다")
    
    try:
        if image_input.startswith('data:image'):
            # Base64 데이터 URL
            header, encoded = image_input.split(',', 1)
            image_data = base64.b64decode(encoded)
        elif image_input.startswith('http'):
            # HTTP URL
            response = requests.get(image_input, timeout=30)
            response.raise_for_status()
            image_data = response.content
        else:
            # 일반 Base64 문자열
            image_data = base64.b64decode(image_input)
        
        # PIL Image로 로드
        image = Image.open(BytesIO(image_data))
        
        # RGBA인 경우 RGB로 변환
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 임시 파일로 저장
        temp_dir = tempfile.gettempdir()
        temp_filename = f"source_image_{hash(image_input) % 100000}.jpg"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        image.save(temp_path, 'JPEG', quality=95)
        
        print(f"이미지 저장 완료: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"이미지 로드 실패: {str(e)}")
        raise ValueError(f"이미지를 로드할 수 없습니다: {str(e)}")


def load_video_from_input(video_input):
    """
    Base64 인코딩된 문자열이나 URL에서 영상을 로드하고 임시 파일로 저장
    
    Args:
        video_input: Base64 문자열 또는 영상 URL
        
    Returns:
        str: 저장된 영상 파일 경로
    """
    
    if not video_input:
        raise ValueError("영상 입력이 없습니다")
    
    try:
        if video_input.startswith('data:video'):
            # Base64 데이터 URL
            header, encoded = video_input.split(',', 1)
            video_data = base64.b64decode(encoded)
        elif video_input.startswith('http'):
            # HTTP URL
            response = requests.get(video_input, timeout=60)
            response.raise_for_status()
            video_data = response.content
        else:
            # 일반 Base64 문자열
            video_data = base64.b64decode(video_input)
        
        # 임시 파일로 저장
        temp_dir = tempfile.gettempdir()
        temp_filename = f"driving_video_{hash(video_input) % 100000}.mp4"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        with open(temp_path, 'wb') as f:
            f.write(video_data)
        
        print(f"영상 저장 완료: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"영상 로드 실패: {str(e)}")
        raise ValueError(f"영상을 로드할 수 없습니다: {str(e)}")


# 이전 버전과의 호환성을 위한 alias
ImageToVideoConverter = LivePortraitConverter


def main():
    """CLI 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LivePortrait CLI - 이미지와 영상을 사용해 LivePortrait 영상 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 사용법
  python action.py -s source.jpg -d driving.mp4 -o output/

  # 고급 설정
  python action.py -s source.jpg -d driving.mp4 -o output/ \\
    --driving-option pose-friendly \\
    --driving-multiplier 1.5 \\
    --animation-region exp \\
    --no-stitching

  # Base64 입력 (URL도 가능)
  python action.py -s "data:image/jpeg;base64,/9j/4AAQ..." \\
    -d "https://example.com/driving.mp4" -o output/

파일 형식:
  소스 이미지: JPG, JPEG, PNG
  드라이빙 영상: MP4, AVI, MOV
        """
    )
    
    # 필수 인자
    parser.add_argument('-s', '--source', required=True,
                       help='소스 이미지 파일 경로, URL, 또는 Base64 문자열')
    parser.add_argument('-d', '--driving', required=True,
                       help='드라이빙 영상 파일 경로, URL, 또는 Base64 문자열')
    parser.add_argument('-o', '--output', required=True,
                       help='출력 디렉토리')
    
    # LivePortrait 설정
    parser.add_argument('--driving-option', choices=['expression-friendly', 'pose-friendly'],
                       default='expression-friendly',
                       help='드라이빙 옵션 (기본값: expression-friendly)')
    parser.add_argument('--driving-multiplier', type=float, default=1.0,
                       help='드라이빙 승수 (기본값: 1.0)')
    parser.add_argument('--animation-region', choices=['exp', 'pose', 'lip', 'eyes', 'all'],
                       default='all',
                       help='애니메이션 영역 (기본값: all)')
    parser.add_argument('--audio-priority', choices=['source', 'driving'],
                       default='driving',
                       help='오디오 우선순위 (기본값: driving)')
    
    # 플래그 옵션들
    parser.add_argument('--no-half-precision', action='store_true',
                       help='반정밀도(FP16) 비활성화')
    parser.add_argument('--crop-driving-video', action='store_true',
                       help='드라이빙 영상 크롭 활성화')
    parser.add_argument('--force-cpu', action='store_true',
                       help='CPU 강제 사용')
    parser.add_argument('--no-stitching', action='store_true',
                       help='스티칭 비활성화')
    parser.add_argument('--no-relative-motion', action='store_true',
                       help='상대적 모션 비활성화')
    parser.add_argument('--no-pasteback', action='store_true',
                       help='페이스백 비활성화')
    parser.add_argument('--no-crop', action='store_true',
                       help='크롭 비활성화')
    
    # 속도 최적화 옵션
    parser.add_argument('--no-concat', action='store_true',
                       help='비교 영상(concat) 생성 비활성화 - 처리 속도 향상')
    parser.add_argument('--save-concat', action='store_true',
                       help='비교 영상(concat) 생성 활성화 - 드라이빙+소스+결과 나란히 보기')
    
    # 크롭 설정
    parser.add_argument('--scale', type=float, default=2.3,
                       help='소스 크롭 스케일 (기본값: 2.3)')
    parser.add_argument('--source-max-dim', type=int, default=1280,
                       help='소스 최대 해상도 (기본값: 1280)')
    
    # 디바이스 설정
    parser.add_argument('--device-id', type=int, default=0,
                       help='GPU 디바이스 ID (기본값: 0)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 LivePortrait CLI 시작")
        print(f"  소스: {args.source[:50]}...")
        print(f"  드라이빙: {args.driving[:50]}...")
        print(f"  출력: {args.output}")
        print(f"  설정: {args.driving_option}, 승수: {args.driving_multiplier}")
        
        # 입력 파일 처리
        print("\n📁 입력 파일 처리 중...")
        
        # 소스 이미지 처리
        if args.source.startswith(('http', 'data:')):
            source_path = load_image_from_input(args.source)
        else:
            if not osp.exists(args.source):
                raise FileNotFoundError(f"소스 이미지를 찾을 수 없습니다: {args.source}")
            source_path = args.source
        
        # 드라이빙 영상 처리
        if args.driving.startswith(('http', 'data:')):
            driving_path = load_video_from_input(args.driving)
        else:
            if not osp.exists(args.driving):
                raise FileNotFoundError(f"드라이빙 영상을 찾을 수 없습니다: {args.driving}")
            driving_path = args.driving
        
        print(f"✅ 소스 이미지: {source_path}")
        print(f"✅ 드라이빙 영상: {driving_path}")
        
        # LivePortraitConverter 초기화
        print("\n🎭 LivePortraitConverter 초기화 중...")
        converter = LivePortraitConverter()
        
        # 설정 구성
        kwargs = {
            'flag_use_half_precision': not args.no_half_precision,
            'flag_crop_driving_video': args.crop_driving_video,
            'device_id': args.device_id,
            'flag_force_cpu': args.force_cpu,
            'flag_stitching': not args.no_stitching,
            'flag_relative_motion': not args.no_relative_motion,
            'flag_pasteback': not args.no_pasteback,
            'flag_do_crop': not args.no_crop,
            'driving_option': args.driving_option,
            'driving_multiplier': args.driving_multiplier,
            'audio_priority': args.audio_priority,
            'animation_region': args.animation_region,
            'scale': args.scale,
            'source_max_dim': args.source_max_dim,
            
            # concat 설정 (속도 최적화)
            'flag_save_concat_video': args.save_concat and not args.no_concat,
        }
        
        # 영상 변환 실행
        print("\n⚡ LivePortrait 변환 시작...")
        output_path = converter.convert_image_video_to_video(
            source_image_path=source_path,
            driving_video_path=driving_path,
            output_dir=args.output,
            **kwargs
        )
        
        print(f"\n🎉 성공! 결과 영상: {output_path}")
        
        # 파일 정보 출력
        if osp.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📁 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # 임시 파일 정리
        if args.source.startswith(('http', 'data:')) and osp.exists(source_path):
            os.remove(source_path)
            print("🧹 임시 소스 이미지 파일 정리됨")
        
        if args.driving.startswith(('http', 'data:')) and osp.exists(driving_path):
            os.remove(driving_path)
            print("🧹 임시 드라이빙 영상 파일 정리됨")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
