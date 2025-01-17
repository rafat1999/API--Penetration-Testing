[English](./README.md) | [繁中版](./README-tw.md) | [العربية](./README-ar.md) | [Azərbaycan](./README-az.md) | [Български](./README-bg.md) | [বাংলা](./README-bn.md) | [Català](./README-ca.md) | [Čeština](./README-cs.md) | [Deutsch](./README-de.md) | [Ελληνικά](./README-el.md) | [Español](./README-es.md) | [فارسی](./README-fa.md) | [Français](./README-fr.md) | [हिंदी](./README-hi.md) | [Indonesia](./README-id.md) | [Italiano](./README-it.md) | [日本語](./README-ja.md) | [한국어](./README-ko.md) | [ພາສາລາວ](./README-lo.md) | [Македонски](./README-mk.md) | [മലയാളം](./README-ml.md) | [Монгол](./README-mn.md) | [Nederlands](./README-nl.md) | [Polski](./README-pl.md) | [Português (Brasil)](./README-pt_BR.md) | [Русский](./README-ru.md) | [ไทย](./README-th.md) | [Türkçe](./README-tr.md) | [Українська](./README-uk.md) | [Tiếng Việt](./README-vi.md)

# 开发安全的 API 所需要核对的清单

以下是当你在设计，测试以及发布你的 API 的时候所需要核对的重要安全措施。

---

## 身份认证

- [ ] 不要使用 `Basic Auth` ，请使用标准的认证协议（如 [JWT](https://jwt.io/)，[OAuth](https://oauth.net/)）。
- [ ] 不要重新实现 `Authentication`、`token generating` 和 `password storage`，请使用标准库。
- [ ] 限制密码错误尝试次数，并且增加账号冻结功能。
- [ ] 密码或账号登录失败时返回模糊的提示信息，防止暴力破解攻击。
- [ ] 加密所有的敏感数据。
- [ ] 不要将API Key，云组件Key等硬编码到前端页面或APP中。
- [ ] 使用开源框架时禁止使用默认Key，比如Shiro。

### JWT（JSON Web Token）

- [ ] 使用随机复杂的密钥（`JWT Secret`）以增加暴力破解的难度。
- [ ] 不要在请求体中直接提取数据，要对数据进行加密（`HS256` 或 `RS256`）。
- [ ] 使 token 的过期时间尽量的短（`TTL`，`RTTL`）。
- [ ] 不要在 JWT 的请求体中存放敏感数据，因为它是[可解码的](https://jwt.io/#debugger-io)。
- [ ] 避免存储过多的数据。 JWT 通常在标头中共享，并且它们有大小限制。

## 访问

- [ ] 限制流量来防止 DDoS 攻击和暴力攻击。
- [ ] 对API接口访问进行速率限制防止业务数据被批量爬取。
- [ ] 在服务端使用 HTTPS 协议来防止 MITM （中间人攻击）。
- [ ] 使用 `HSTS` 协议防止 SSL Strip 攻击。
- [ ] 关闭目录列表。
- [ ] 禁止公开存储文件列表可未授权访问。
- [ ] 对于私有 API，仅允许从列入白名单的 IP/主机进行访问。
- [ ] 禁止将内部组件接口、登录管理接口暴露于公网中。
- [ ] 禁止将SourceMap文件暴露到公网中。
- [ ] 禁止将API接口描述文档暴露到公网中。

## Authorization

### OAuth 授权或认证协议

- [ ] 始终在后台验证 `redirect_uri`，只允许白名单的 URL。
- [ ] 始终在授权时使用有效期较短的授权码（code）而不是令牌（access_token）（不允许 `response_type=token`）。
- [ ] 使用随机哈希数的 `state` 参数来防止跨站请求伪造（CSRF）。
- [ ] 对不同的应用分别定义默认的作用域和各自有效的作用域参数。

## 输入

- [ ] 使用与操作相符的 HTTP 操作函数，`GET（读取)`，`POST（创建）`，`PUT（替换/更新）` 以及 `DELETE（删除记录）`，如果请求的方法不适用于请求的资源则返回 `405 Method Not Allowed`。
- [ ] 在请求头中的 `content-type` 字段使用内容验证来只允许支持的格式（如 `application/xml`，`application/json` 等等）并在不满足条件的时候返回 `406 Not Acceptable`。
- [ ] 验证 `content-type` 中申明的编码和你收到正文编码一致（如 `application/x-www-form-urlencoded`，`multipart/form-data`，`application/json` 等等）。
- [ ] 验证用户输入来避免一些普通的易受攻击缺陷（如 `XSS`，`SQL-注入`，`远程代码执行` 等等）。
- [ ] 不要在 URL 中使用任何敏感的数据（`credentials`，`Passwords`，`security tokens`，or `API keys`），而是使用标准的认证请求头。
- [ ] 仅使用服务器端加密。
- [ ] 使用一个 API Gateway 服务来启用缓存、限制访问速率（如 `Quota`，`Spike Arrest`，`Concurrent Rate Limit`）以及动态地部署 APIs resources。

## 处理

- [ ] 检查是否所有的接口都包含必要都身份认证，以避免被破坏了的认证体系。
- [ ] 避免使用特有的资源 id。使用 `/me/orders` 替代 `/user/654321/orders`。
- [ ] 使用 `UUID` 代替自增长的 id。
- [ ] 对于访问资源进行权限检查，防止横向越权。
- [ ] 如果需要解析 XML 文件，确保实体解析（entity parsing）是关闭的以避免 `XXE` 攻击。
- [ ] 如果需要解析 XML 文件，确保实体扩展（entity expansion）是关闭的以避免通过指数实体扩展攻击实现的 `Billion Laughs/XML bomb`。
- [ ] 在文件上传中使用 CDN。
- [ ] 如果数据处理量很大，尽可能使用队列或者 Workers 在后台处理来避免阻塞请求，从而快速响应客户端。
- [ ] 不要忘了把 DEBUG 模式关掉。
- [ ] 可用时使用不可执行的堆栈。
- [ ] 禁止使用类似于PHP `extract`函数将接口输入参数转换为变量。

## 输出

- [ ] 增加请求返回头 `X-Content-Type-Options: nosniff`。
- [ ] 增加请求返回头 `X-Frame-Options: deny`。
- [ ] 增加请求返回头 `Content-Security-Policy: default-src 'none'`。
- [ ] 删除请求返回中的指纹头 - `X-Powered-By`，`Server`，`X-AspNet-Version` 等等。
- [ ] 在响应中遵循请求的 `content-type`，如果你的请求类型是 `application/json` 那么你返回的 `content-type` 就是 `application/json`。
- [ ] 不要返回敏感的数据，如 `credentials`，`Passwords`，`security tokens`。
- [ ] 给请求返回使用合理的 HTTP 响应代码。（如 `200 OK`，`400 Bad Request`，`401 Unauthorized`，`405 Method Not Allowed` 等等）。
- [ ] 返回统一的错误页面，误将调用堆栈等信息在错误页面中展示。
- [ ] 仅返回前端需要的业务数据，禁止返回过多类型敏感数据。
- [ ] 前端对敏感业务数据使用时应结合业务需求对敏感数据进行脱敏。
- [ ] 禁止在前端对数据进行脱敏，数据返回时在后端进行脱敏。

## 持续集成和持续部署

- [ ] 使用单元测试以及集成测试的覆盖率来保障你的设计和实现。
- [ ] 引入代码审查流程，禁止私自合并代码。
- [ ] 在推送到生产环境之前确保服务的所有组件都用杀毒软件静态地扫描过，包括第三方库和其它依赖。
- [ ] 对您的代码持续运行安全测试（静态/动态分析）。
- [ ] 检查您的依赖项（软件和操作系统）是否存在已知漏洞。
- [ ] 为部署设计一个回滚方案。

## 监控

- [ ] 对所有服务和组件使用集中式登录。
- [ ] 使用代理来监控所有流量、错误、请求和响应。
- [ ] 使用短信，Slack，电子邮件，电报，Kibana, Cloudwatch等提醒。
- [ ] 确保你没有记录任何敏感数据，如信用卡、密码、pin等。
- [ ] 使用IDS和/或IPS系统监视您的API请求和实例。
- [ ] 使用API检测设备进行API资产梳理、日志审计。

---

## 也可以看看

- [yosriady/api-development-tools](https://github.com/yosriady/api-development-tools) - 用于构建 RESTful HTTP + JSON API 的有用资源集合。

---

# 贡献

为此存储库创建一个 fork，进行修改，并提交 pull request 来贡献。如果您有任何问题，请发送邮件至 `team@shieldfy.io`。
