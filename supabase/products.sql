-- ========================================================== --
-- H&B PRODUCTS 목업 데이터 생성 SQL 스크립트                   --
-- 설명: 리뷰 데이터의 부모 데이터로 작동하는 올리브영 기반       --
--       대표 뷰티 상품 10개에 대한 INSERT 구문입니다.        --
--       중복 방지를 위한 ON CONFLICT 제약 조건을 추가했습니다. --
-- ========================================================== --

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('e680f731-cfde-427f-9077-62f7e484ec21', '독도 저자극 토너 & 로션 듀오 기획 세트', '울릉도 해양심층수의 풍부한 미네랄로 피부를 순하고 촉촉하게 가꿔주는 저자극 수분 듀오 세트', 32000, now() - interval '34 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('0c85306c-89fa-4a83-9e16-5540ee3b68aa', '히알루론산 딥 모이스처 수분 크림 100ml 대용량', '8중 복합 히알루론산으로 피부 속 깊이 촘촘하게 수분막을 형성해주는 무향 수분크림', 28000, now() - interval '15 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('63d4efec-06f6-43d2-93b4-11b26b88c9e3', '시카 릴리프 카밍 에센스 50ml', '고농축 병풀 추출물(CICA)과 마데카소사이드 성분이 붉어지고 예민해진 피부를 빠르게 진정시키는 카밍 에센스', 24000, now() - interval '42 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('cda7adcd-30e5-4610-8dd6-d1b48a3e018a', '데일리 무기자차 마일드 선크림 SPF50+ PA++++', '눈시림 없이 온 가족이 사용할 수 있는 백탁 없는 순한 데일리 물리적 자외선 차단제', 19800, now() - interval '23 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('833d50fc-4c16-42df-8745-72b36f305dd6', '비타민C 시트러스 브라이트닝 잡티 세럼', '순수 비타민C와 나이아신아마이드 배합으로 칙칙한 잡티와 기미를 케어해주는 고농축 미백 세럼', 35000, now() - interval '49 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('116a021c-1268-441d-aa30-ec5c87156e12', '고영양 무향 허니 데일리 모이스처 립밤 듀오', '트고 갈라진 입술에 풍부한 시어버터와 꿀 추출물로 영양을 가득 채우는 스틱형 촉촉 립밤', 12000, now() - interval '12 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('a9f84554-81bd-4252-89af-f3c91733406a', '이너뷰티 저분자 콜라겐 & 유산균 30포', '하루 한 포로 챙기는 흡수율 높은 300달톤 저분자 피쉬콜라겐과 포스트바이오틱스 복합 이너뷰티', 26900, now() - interval '47 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('04472697-d7c5-4cbe-bbc1-3cb62d3d4eba', '티트리 트러블 진정 퀵 카밍 패드 80매', '제주산 티트리 추출물을 가득 머금어 트러블 부위를 빠르게 진정시키고 각질을 케어하는 비건 인증 패드', 22000, now() - interval '45 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('1adcc870-2ca1-4731-a698-2e1ac3451eae', '약산성 리프레싱 약쑥 클렌징 폼 200ml', '강화 약쑥 추출물의 편안함과 조밀한 약산성 거품으로 세안 후에도 당김 없이 노폐물을 세정하는 약산성 폼', 15000, now() - interval '45 days', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.products (id, name, description, price, created_at, updated_at) VALUES 
('ca7292aa-6e29-4772-8481-4ff1ace806a6', '아르간 손상 모발 집중 케어 헤어 에센스 오일 120ml', '손상되고 푸석한 모발에 아르간 오일과 실크 단백질을 공급하여 끈적임 없이 빛나는 윤기를 부여하는 헤어 오일', 18000, now() - interval '48 days', now())
ON CONFLICT (id) DO NOTHING;
