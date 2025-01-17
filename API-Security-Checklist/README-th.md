[English](./README.md) | [繁中版](./README-tw.md) | [简中版](./README-zh.md) | [العربية](./README-ar.md) | [Azərbaycan](./README-az.md) | [Български](./README-bg.md) | [বাংলা](./README-bn.md) | [Català](./README-ca.md) | [Čeština](./README-cs.md) | [Deutsch](./README-de.md) | [Ελληνικά](./README-el.md) | [Español](./README-es.md) | [فارسی](./README-fa.md) | [Français](./README-fr.md) | [हिंदी](./README-hi.md) | [Indonesia](./README-id.md) | [Italiano](./README-it.md) | [日本語](./README-ja.md) | [한국어](./README-ko.md) | [ພາສາລາວ](./README-lo.md) | [Македонски](./README-mk.md) | [മലയാളം](./README-ml.md) | [Монгол](./README-mn.md) | [Nederlands](./README-nl.md) | [Polski](./README-pl.md) | [Português (Brasil)](./README-pt_BR.md) | [Русский](./README-ru.md) | [Türkçe](./README-tr.md) | [Українська](./README-uk.md) | [Tiếng Việt](./README-vi.md)

# API Security Checklist

Checklist ที่ต้องให้ความสำคัญเมื่อมีการสร้าง API ในช่วงการออกแบบ ทดสอบระบบ และการปล่อยให้คนนอกใช้

---

## Authentication (การพิสูจน์ตัวตน)

- [ ] ไม่ควรใช้ `Basic Auth` (การ authen ปกติด้วยusername password) สำหรับการพิสูจน์ตัวตน แต่ให้ใช้รูปแบบมาตรฐานสากลแทน(e.g. JWT, OAuth).
- [ ] ไม่ต้องเสียเวลาสร้างวิธี Authentication ใหม่ขึ้นมา ให้ใช้ที่มีอยู่ในมาตรฐานไปเลย
- [ ] ให้มีการจำกัดจำนวนครั้งในการพยายาม authen และสร้างระบบล็อคกรณีพยายามเกินกำหนด
- [ ] ข้อมูลที่สำคัญควรมีการเข้ารหัสเสมอ

### JWT (JSON Web Token)

- [ ] key ในการ generate token ควรมีความซับซ้อนสูง เพื่อป้องกันการ brute force หาตัวเข้ารหัส
- [ ] ไม่ควรมีการแกะข้อมูลหรือขั้นตอนการถอดข้อมูลในฝั่ง client. ให้มีเฉพาะในฝั่ง server เท่านั้น โดยอาจใช้วิธีเข้ารหัสด้วย HS256 หรือ RS256 เอา
- [ ] พยายามให้ token หมดอายุให้ไวที่สุดเท่าที่จะเป็นไปได้ (`TTL`, `RTTL`)
- [ ] ไม่ควรเก็บข้อมูลสำคัญใน payload ของ JWT เพราะอาจถูกแกะได้ [ง่าย](https://jwt.io/#debugger-io).
- [ ] หลีกเลี่ยงการจัดเก็บข้อมูลมากเกินไป. JWT มักใช้ร่วมกันใน header และมีขนาดจำกัด.

## Access

- [ ] จำกัดจำนวนสูงสุดของ request เพื่อป้องกัน DDoS / Bruteforce.
- [ ] ใช้ https เพื่อป้องกัน MITM (Man In The Middle Attack).
- [ ] ใช้ `HSTS` header กับ SSL เพื่อป้องกัน SSL Strip attack.
- [ ] ปิดรายการไดเรกทอรี.
- [ ] สำหรับ API ส่วนตัว อนุญาตการเข้าถึงจาก IP/โฮสต์ที่อนุญาตพิเศษเท่านั้น.

## Authorization

### OAuth

- [ ] มีการ validate `redirect_uri` ในฝั่ง server โดยยอมรับuriเฉพาะที่มีอยู่ในลิสต์ที่เราเชื่อถือเท่านั้น (whitelist).
- [ ] บังคับให้มีการใช้ response_type เป็น code เสมอ (พยายามเลี่ยง `response_type=token`).
- [ ] ตัวแปร `state` ให้ใช้ random hash เพื่อป้องกัน CSRF (Cross Site Request Forgery) ในช่วง OAuth authentication.
- [ ] กำหนด scope และมีการ validate scope ตัวแปรสำหรับแต่ละแอป.

## Input

- [ ] ใช้คำสั่ง HTTP ตาม operation ที่ทำ เช่น `GET (read)`, `POST (create)`, `PUT/PATCH (replace/update)` and `DELETE (to delete a record)` และตอบกลับด้วย `405 Method Not Allowed` ถ้าไม่มีการรองรับ request ด้วย method นั้นในระบบ.
- [ ] Validate `content-type` ใน header ขา request (Content Negotiation) โดยยอมให้ส่งมาเฉพาะ format ที่กำหนด (e.g. `application/xml`, `application/json`... และอื่นๆ) และตอบกลับด้วย `406 Not Acceptable` ถ้า format ที่ส่งมาไม่ถูก.
- [ ] Validate `content-type` ของ data ที่รับมาทุกครั้ง(e.g. `application/x-www-form-urlencoded`, `multipart/form-data ,application/json`... ).
- [ ] Validate ข้อมูลที่ user ใส่เข้ามาทุกครั้งเพื่อป้องกันช่องโหว่ที่โดนกันบ่อยๆ (e.g. `XSS`, `SQL-Injection`, `Remote Code Execution` ... etc).
- [ ] ห้ามเอาข้อมูลสำคัญไปใส่ไว้ใน URL (เช่น /servicexxx?creditcardnum=1234) แต่ให้ไปแปะไว้ใน authorization header แทน (`credentials`, `Passwords`, `security tokens`, หรือ `API keys`)
- [ ] ใช้การเข้ารหัสฝั่งเซิร์ฟเวอร์เท่านั้น.
- [ ] ทำ API Gateway เพื่อให้สามารถทำ caching, Rate Limit, Spike Arrest, และการจัดสรรค์ทรัพยากรสำหรับ API ได้อย่างยืดหยุ่น.

## Processing

- [ ] ตรวจดูว่า endpoints ทุกจุดอยู่ภายใต้ authentication เพื่อป้องกันช่องโหว่ที่ทำให้คนอื่นมาเรียกใช้โดยไม่จำเป็นต้องพิสูจน์ตัวตน.
- [ ] ไม่ควรนำ resource ID ของ user ไปใช้ (`/user/654321/orders`) แต่ให้ไปใช้แบบ `/me/orders` แทน เพื่อป้องกัน user เปลี่ยนไปใช้ของคนอื่น.
- [ ] เลข ID ของ user ไม่ควรมีการสร้างแบบไล่ลำดับเพิ่มไปเรื่อยๆ แต่ให้สร้าง UUID แทน.
- [ ] If you are parsing XML data, make sure entity parsing is not enabled to avoid `XXE` (XML external entity attack).
- [ ] ถ้ามีการ parsing ไฟล์ XML, ให้ปิดส่วนของ Entity parsing ไว้เพื่อเลี่ยงที่จะโดนช่องโหว่ต่างๆเช่น (XML external entity attack, Billion Laughs/XML bomb).
- [ ] ใช้ CDN เมื่อจำเป็นต้องมีการ upload ไฟล์จาก client.
- [ ] หากต้องเผชิญกับข้อมูลขนาดใหญ่ ให้ใช้ Workers กับ คิวในการจัดการเพื่อให้มีการตอบข้อมูลกลับได้อย่างรวดเร็วจะได้ไม่เกิดคอขวดขึ้น.
- [ ] อย่าลืมปิดโหมด DEBUG ใน code หากทำไว้.
- [ ] ใช้ stack ที่ไม่สามารถเรียกใช้งานได้เมื่อมี.

## Output

- [ ] ตั้ง `X-Content-Type-Options: nosniff` ใน header.
- [ ] ตั้ง `X-Frame-Options: deny` ใน header.
- [ ] ตั้ง `Content-Security-Policy: default-src 'none'` ในheader.
- [ ] เอา fingerprinting headers ออก - `X-Powered-By`, `Server`, `X-AspNet-Version` etc.
- [ ] กำหนด content-type ใน response เช่นถ้าต้องการส่งข้อมูลที่เป็น json กลับไป ก็เซ็ต `content-type` เป็น `application/json` ไปเลย
- [ ] ไม่ต้องส่งข้อมูลส่งข้อมูลสำคัญกลับไปหา client (`credentials`, `Passwords`, `security tokens`).
- [ ] ตอบ status code ที่ตรงกับ operation กลับไป (e.g. `200 OK`, `400 Bad Request`, `401 Unauthorized`, `405 Method Not Allowed` ... etc).

## CI & CD

- [ ] ตรวจสอบ design กับ implementation ในขั้น unit/integration test อย่างครอบคลุม
- [ ] ให้ใช้ code review process ไม่ใช่ว่าตัวเองพอใจก็โอเคแล้ว
- [ ] มั่นใจว่าทุกอย่างใน service ปลอดไวรัสแล้วก่อนจะนำขึ้น production รวมถึง lib ของพวก vendor กับ dependencies อื่นๆด้วย
- [ ] เรียกใช้การทดสอบความปลอดภัยอย่างต่อเนื่อง (การวิเคราะห์แบบสแตติก/ไดนามิก) ในโค้ดของคุณ.
- [ ] ตรวจสอบการพึ่งพาของคุณ (ทั้งซอฟต์แวร์และระบบปฏิบัติการ) เพื่อหาช่องโหว่ที่ทราบ.
- [ ] ออกแบบวิธี rollback ไว้ด้วยก่อนจะนำขึ้นไป เพราะเวลาเกิดปัญหาจะได้ย้อนกลับมาใช้ version เก่าไปก่อนได้ (อาจพบได้บ่อยตอนพัฒนา feature ใหม่ๆ)

## Monitoring

- [ ] Use centralized logins for all services and components.
- [ ] Use agents to monitor all traffic, errors, requests, and responses.
- [ ] Use alerts for SMS, Slack, Email, Telegram, Kibana, Cloudwatch, etc.
- [ ] Ensure that you aren't logging any sensitive data like credit cards, passwords, PINs, etc.
- [ ] Use an IDS and/or IPS system to monitor your API requests and instances.

---

## ดูสิ่งนี้ด้วย:

- [yosriady/api-development-tools](https://github.com/yosriady/api-development-tools) - ชุดของแหล่งข้อมูลที่เป็นประโยชน์สำหรับการสร้าง API RESTful HTTP+JSON.

---

# Contribution

Feel free to contribute by forking this repository, making some changes, and submitting pull requests. For any questions drop us an email at `team@shieldfy.io`.
