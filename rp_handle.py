
import base64
import os
import json
from action import LivePortraitConverter, load_image_from_input, load_video_from_input

# RunPod import with fallback for testing
try:
    import runpod
    RUNPOD_AVAILABLE = True
except ImportError:
    print("⚠️  RunPod not available - running in test mode")
    RUNPOD_AVAILABLE = False
    
    # Mock RunPod for testing
    class MockRunPod:
        @staticmethod
        def serverless():
            return MockRunPodServerless()
    
    class MockRunPodServerless:
        @staticmethod
        def start(config):
            print("🧪 Mock RunPod serverless start - testing mode")
            # Test mode: read from test_input.json
            if os.path.exists('test_input.json'):
                print("📋 test_input.json 파일 발견 - 테스트 모드로 실행")
                with open('test_input.json', 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                
                handler = config['handler']
                result = handler(test_data)
                
                # 결과를 JSON 파일로 저장 (테스트에서 안정적으로 읽을 수 있도록)
                output_file = 'test_output.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✅ 결과가 {output_file}에 저장되었습니다.")
                
                # 콘솔에도 출력 (기존 동작 유지)
                print("Handler output:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            else:
                print("❌ test_input.json 파일이 없습니다.")
                return None
    
    runpod = MockRunPod()

def handler(job):
    """RunPod 핸들러 함수 - LivePortrait를 사용한 이미지-영상 변환"""
    try:
        # 입력 데이터 파싱
        job_input = job.get('input', {})
        source_image = job_input.get('source_image', '')  # 소스 이미지 (Base64 또는 URL)
        driving_video = job_input.get('driving_video', '')  # 드라이빙 영상 (Base64 또는 URL)
        
        # LivePortrait 설정 옵션들
        flag_use_half_precision = job_input.get('flag_use_half_precision', True)
        flag_crop_driving_video = job_input.get('flag_crop_driving_video', False)
        device_id = job_input.get('device_id', 0)
        flag_force_cpu = job_input.get('flag_force_cpu', False)
        flag_stitching = job_input.get('flag_stitching', True)
        flag_relative_motion = job_input.get('flag_relative_motion', True)
        flag_pasteback = job_input.get('flag_pasteback', True)
        flag_do_crop = job_input.get('flag_do_crop', True)
        driving_option = job_input.get('driving_option', "expression-friendly")
        driving_multiplier = job_input.get('driving_multiplier', 1.0)
        audio_priority = job_input.get('audio_priority', 'driving')
        animation_region = job_input.get('animation_region', "all")
        
        # 속도 최적화 옵션
        flag_save_concat_video = job_input.get('flag_save_concat_video', False)  # 기본적으로 concat 비활성화로 속도 향상
        
        # 입력 검증
        if not source_image:
            raise ValueError("source_image is required")
        if not driving_video:
            raise ValueError("driving_video is required")
        
        print(f"LivePortrait 처리 시작")
        print(f"  - 설정: {driving_option}, multiplier: {driving_multiplier}")
        print(f"  - 애니메이션 영역: {animation_region}")
        
        # 이미지와 영상을 임시 파일로 저장
        print("입력 파일 처리 중...")
        source_image_path = load_image_from_input(source_image)
        driving_video_path = load_video_from_input(driving_video)
        
        # LivePortraitConverter 생성 및 영상 변환
        print("LivePortraitConverter 초기화 중...")
        converter = LivePortraitConverter()
        
        print("LivePortrait 변환 실행 중...")
        
        # 현재 디렉토리에 출력 폴더 생성
        current_output_dir = os.path.join(os.getcwd(), "liveportrait_output")
        os.makedirs(current_output_dir, exist_ok=True)
        print(f"📁 출력 디렉토리: {current_output_dir}")
        
        output_video_path = converter.convert_image_video_to_video(
            source_image_path=source_image_path,
            driving_video_path=driving_video_path,
            output_dir=current_output_dir,  # 현재 디렉토리의 출력 폴더 지정
            flag_use_half_precision=flag_use_half_precision,
            flag_crop_driving_video=flag_crop_driving_video,
            device_id=device_id,
            flag_force_cpu=flag_force_cpu,
            flag_stitching=flag_stitching,
            flag_relative_motion=flag_relative_motion,
            flag_pasteback=flag_pasteback,
            flag_do_crop=flag_do_crop,
            driving_option=driving_option,
            driving_multiplier=driving_multiplier,
            audio_priority=audio_priority,
            animation_region=animation_region,
            flag_save_concat_video=flag_save_concat_video
        )
        
        # 현재 디렉토리에 최종 결과 파일 복사 (접근 편의성)
        import shutil
        final_output_filename = f"liveportrait_result_{hash(source_image + driving_video) % 100000}.mp4"
        final_output_path = os.path.join(os.getcwd(), final_output_filename)
        
        shutil.copy2(output_video_path, final_output_path)
        print(f"📁 최종 결과 파일: {final_output_path}")
        
        # 생성된 비디오 파일을 base64로 인코딩
        print("비디오를 Base64로 인코딩 중...")
        with open(output_video_path, 'rb') as video_file:
            video_b64 = base64.b64encode(video_file.read()).decode('utf-8')
      
        print("처리 완료! 비디오 경로:", output_video_path)
        print(f"📂 현재 디렉토리 결과: {final_output_path}")
        
        # 파일 정보 수집
        file_size = os.path.getsize(output_video_path)
        
        # 임시 파일 정리
        try:
            if os.path.exists(source_image_path):
                os.remove(source_image_path)
            if os.path.exists(driving_video_path):
                os.remove(driving_video_path)
        except Exception as cleanup_error:
            print(f"임시 파일 정리 중 오류: {cleanup_error}")
        
        return {
            'status': 'success',
            'output': {
                'success': True,
                'video_base64': video_b64,
                'file_size_bytes': file_size,
                'source_image_processed': True,
                'driving_video_processed': True,
                'driving_option': driving_option,
                'driving_multiplier': driving_multiplier,
                'animation_region': animation_region,
                'audio_priority': audio_priority,
                'job_id': f"liveportrait_{hash(source_image + driving_video) % 100000}"
            }
        }
        
    except Exception as e:
        error_msg = f"오류 발생: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        return {
            'status': 'error',
            'output': {
                'success': False,
                'error': error_msg
            }
        }

# RunPod 서버리스 환경에서 실행
runpod.serverless.start({'handler': handler})