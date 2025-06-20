#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import base64
import json
import subprocess
import sys
from datetime import datetime
import time
import ast

def image_to_base64(image_path):
    """이미지 파일을 base64로 변환"""
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/jpeg;base64,{image_base64}"

def base64_to_image(base64_string, output_path):
    """base64 문자열을 이미지 파일로 저장"""
    if base64_string.startswith('data:image'):
        base64_string = base64_string.split(',')[1]
    
    image_data = base64.b64decode(base64_string)
    with open(output_path, 'wb') as f:
        f.write(image_data)

def base64_to_video(base64_string, output_path):
    """base64 문자열을 비디오 파일로 저장"""
    if base64_string.startswith('data:video'):
        base64_string = base64_string.split(',')[1]
    
    video_data = base64.b64decode(base64_string)
    with open(output_path, 'wb') as f:
        f.write(video_data)

def video_to_base64(video_path):
    """비디오 파일을 base64로 변환"""
    with open(video_path, 'rb') as video_file:
        video_data = video_file.read()
        video_base64 = base64.b64encode(video_data).decode('utf-8')
        return f"data:video/mp4;base64,{video_base64}"

def create_test_input_json():
    """test_input.json 파일 생성"""
    print("📋 test_input.json 생성 중...")
    
    # 기존 test_input.json 파일 확인 및 제거
    if os.path.exists("test_input.json"):
        print("⚠️  기존 test_input.json 발견 - 덮어쓰기 진행")
        os.remove("test_input.json")
    
    # 소스 이미지 확인
    if not os.path.exists("source.png"):
        print("❌ source.png 파일이 없습니다.")
        return False
    print("✅ source.png 발견")
    
    # 드라이빙 비디오 확인
    driving_video_b64 = None
    if os.path.exists("driving.mov"):
        print("✅ driving.mov 발견")
        driving_video_b64 = video_to_base64("driving.mov")
        print(f"✅ driving.mov 변환 완료 (크기: {len(driving_video_b64):,} 문자)")
    else:
        print("❌ driving.mov 파일이 없습니다.")
        return False
    
    # 소스 이미지를 base64로 변환
    print("📷 소스 이미지 변환 중...")
    source_image_b64 = image_to_base64("source.png")
    print(f"✅ 변환 완료 (크기: {len(source_image_b64):,} 문자)")
    
    # RunPod 테스트 입력 데이터 구조 (LivePortrait에 맞춤)
    test_input = {
        "input": {
            "source_image": source_image_b64,
            "driving_video": driving_video_b64,
            "crop_factor": 1.7,
            "driving_smoothing_std": 2.0,
            "source_smoothing_std": 2.0,
            "expression_scale": 1.0,
            "motion_scale": 1.0,
            "crop_mode": "aaaa",
            "dsize": 512,
            "scale": 2.3,
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0
        }
    }
    
    # test_input.json 파일로 저장 (강제 덮어쓰기)
    try:
        with open("test_input.json", "w", encoding="utf-8") as f:
            json.dump(test_input, f, ensure_ascii=False, indent=2)
        
        print("✅ test_input.json 파일 생성 완료!")
        print(f"📁 파일 크기: {os.path.getsize('test_input.json'):,} bytes")
        
        # 파일 내용 검증
        with open("test_input.json", "r", encoding="utf-8") as f:
            verify_data = json.load(f)
        print("✅ 파일 내용 검증 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ test_input.json 생성 실패: {e}")
        return False

def test_runpod_handler():
    """RunPod 서버리스 방식으로 rp_handle.py 테스트"""
    print("🚀 RunPod 서버리스 테스트 시작")
    print("="*50)
    
    # 1. test_input.json 생성
    if not create_test_input_json():
        return
    
    # 2. rp_handle.py 실행
    print("⚡ rp_handle.py 실행 중...")
    start_time = datetime.now()
    
    try:
        # 환경 변수 설정
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Python 출력 버퍼링 비활성화
        
        # rp_handle.py를 서브프로세스로 실행
        process = subprocess.Popen(
            [sys.executable, "rp_handle.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 라인 버퍼링
            env=env
        )
        
        # 실시간으로 출력 모니터링
        print("🔄 프로세스 출력 모니터링 시작...")
        all_output = []
        while True:
            # stdout 읽기
            output = process.stdout.readline()
            if output:
                print(f"📝 {output.strip()}")
                all_output.append(output)
            
            # stderr 읽기
            error = process.stderr.readline()
            if error:
                print(f"⚠️  {error.strip()}")
                all_output.append(error)
            
            # 프로세스 종료 확인
            if process.poll() is not None:
                break
            
            # 잠시 대기
            time.sleep(0.1)
        
        # 남은 출력 읽기
        stdout, stderr = process.communicate()
        if stdout:
            print("📝 남은 출력:")
            print(stdout)
            all_output.append(stdout)
        if stderr:
            print("⚠️  남은 에러:")
            print(stderr)
            all_output.append(stderr)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"⏱️  실행 시간: {elapsed:.2f}초")
        print(f"📊 종료 코드: {process.returncode}")
        
        if process.returncode == 0:
            print("✅ RunPod 테스트 성공!")
            
            # 결과 JSON 파일에서 직접 읽기 (더 안정적인 방법)
            try:
                print("🎬 결과 응답 처리 중...")
                
                # test_output.json 파일 확인
                output_json_path = "test_output.json"
                if os.path.exists(output_json_path):
                    print(f"✅ {output_json_path} 파일 발견")
                    
                    # JSON 파일에서 결과 읽기
                    with open(output_json_path, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    print("✅ JSON 파일 파싱 성공!")
                    
                    if response_data.get('status') == 'success':
                        output_data = response_data.get('output', {})
                        video_base64 = output_data.get('video_base64')
                        
                        if video_base64:
                            # 현재 디렉토리에 비디오 파일 저장
                            current_dir = os.getcwd()
                            output_filename = f"liveportrait_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                            output_path = os.path.join(current_dir, output_filename)
                            
                            print(f"💾 비디오 저장 중...")
                            print(f"📁 저장 경로: {output_path}")
                            
                            base64_to_video(video_base64, output_path)
                            
                            # 파일 크기 확인
                            if os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                                print(f"✅ 비디오 파일 저장 완료!")
                                print(f"📁 파일명: {output_filename}")
                                print(f"📂 전체 경로: {output_path}")
                                print(f"📊 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
                                
                                # 추가 정보 출력
                                if 'file_size_bytes' in output_data:
                                    print(f"📏 원본 크기: {output_data['file_size_bytes']:,} bytes")
                                if 'job_id' in output_data:
                                    print(f"🆔 Job ID: {output_data['job_id']}")
                                
                                print("🎉 SUCCESS! LivePortrait 얼굴 애니메이션이 성공적으로 생성되어 현재 디렉토리에 저장되었습니다!")
                                
                                # 결과 JSON 파일 정리
                                try:
                                    os.remove(output_json_path)
                                    print(f"🧹 {output_json_path} 파일 정리 완료")
                                except:
                                    pass
                                    
                            else:
                                print("❌ 비디오 파일 저장 실패")
                        else:
                            print("❌ video_base64 데이터를 찾을 수 없습니다.")
                    else:
                        print(f"❌ 응답 상태: {response_data.get('status')}")
                        if 'output' in response_data and 'error' in response_data['output']:
                            print(f"❌ 오류 내용: {response_data['output']['error']}")
                else:
                    print(f"❌ {output_json_path} 파일을 찾을 수 없습니다.")
                    print("🔍 출력에서 관련 라인 검색:")
                    
                    # 전체 출력 결합하여 오류 확인
                    full_output = ''.join(all_output)
                    lines = full_output.split('\n')
                    for i, line in enumerate(lines):
                        if any(keyword in line.lower() for keyword in ['error', 'traceback', 'exception', 'failed']):
                            print(f"라인 {i}: {line[:200]}...")
                        
            except Exception as e:
                print(f"⚠️  응답 처리 중 오류: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ RunPod 테스트 실패!")
            
    except subprocess.TimeoutExpired:
        print("⏰ 타임아웃 (10분 초과)")
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎯 RunPod 서버리스 테스트 완료!")
    print(f"📂 현재 작업 디렉토리: {os.getcwd()}")
    
    # 현재 디렉토리의 mp4 파일들 표시
    try:
        mp4_files = [f for f in os.listdir('.') if f.endswith('.mp4')]
        if mp4_files:
            print(f"📹 현재 디렉토리의 MP4 파일들:")
            for mp4_file in mp4_files:
                file_size = os.path.getsize(mp4_file)
                print(f"  - {mp4_file} ({file_size:,} bytes)")
        else:
            print("📹 현재 디렉토리에 MP4 파일이 없습니다.")
    except Exception as e:
        print(f"⚠️  파일 목록 확인 중 오류: {e}")

if __name__ == "__main__":
    test_runpod_handler() 