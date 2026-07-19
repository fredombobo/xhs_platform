"""小红书真实浏览器爬虫 - 基于 Playwright"""
import os
import re
import json
import time
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Optional


class RealXiaohongshuCrawler:
    """
    基于 Playwright 的真实小红书爬虫

    - 使用真实浏览器自动化，无需逆向 API 签名
    - 持久化浏览器 Profile，一次登录长期有效
    - 自动滚动加载更多内容
    - 提取搜索结果的真实笔记数据
    """

    # Playwright 用户数据目录（保存登录状态）
    USER_DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "browser_profile"
    )

    def __init__(self, cookie: str = "", headless: bool = True):
        self.cookie = cookie
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None

    @property
    def is_available(self) -> bool:
        """检查 Playwright 是否可用"""
        try:
            import playwright
            return True
        except ImportError:
            return False

    def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            os.makedirs(self.USER_DATA_DIR, exist_ok=True)

            # 使用持久化 context，登录状态自动保存在 USER_DATA_DIR
            self._context = self._playwright.chromium.launch_persistent_context(
                self.USER_DATA_DIR,
                headless=self.headless,
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            # 如果有额外的 cookie，注入到 context
            self._setup_cookies()

    def _parse_cookie_string(self, cookie_str: str) -> List[Dict]:
        """解析 cookie 字符串为 Playwright 格式"""
        cookies = []
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                })
        return cookies

    def _setup_cookies(self):
        """设置额外 cookies 到浏览器 context（persistent context 创建后调用）"""
        if self.cookie and self._context:
            cookies = self._parse_cookie_string(self.cookie)
            if cookies:
                try:
                    self._context.add_cookies(cookies)
                    print(f"  已注入 {len(cookies)} 个 Cookie")
                except Exception as e:
                    print(f"  设置 Cookie 失败: {e}")

    def close(self):
        """关闭浏览器"""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def open_login_window(self):
        """打开一个可见的浏览器窗口让用户手动登录（独立于爬取流程）"""
        if not self.is_available:
            raise RuntimeError("Playwright 未安装")

        print("正在打开浏览器登录窗口...")
        self._ensure_browser()

        page = self._context.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
        print("=" * 60)
        print("  浏览器窗口已打开！请在窗口中扫码登录小红书")
        print("  登录成功后，浏览器会自动关闭")
        print("  不要手动关闭浏览器窗口")
        print("=" * 60)

        # 等待用户完成登录（最多等 3 分钟）
        logged_in = False
        for i in range(180):
            time.sleep(1)
            if not self._check_need_login(page):
                logged_in = True
                print("✅ 检测到登录成功！")
                break
            if i % 30 == 0 and i > 0:
                print(f"  等待登录中... ({i}秒)")

        page.close()

        if logged_in:
            print("登录状态已保存，现在可以使用真实爬取功能了")
            return {"success": True, "message": "登录成功"}
        else:
            print("⚠️  登录超时，请重试")
            return {"success": False, "message": "登录超时，请重试"}

    def search_notes(self, keyword: str, count: int = 50, login_first: bool = False) -> List[Dict]:
        """
        使用真实浏览器搜索小红书笔记。
        不阻塞等待登录——如果需要登录，立即返回空结果并提示。
        """
        if not self.is_available:
            raise RuntimeError("Playwright 未安装")

        print(f"[真实浏览器] 搜索: {keyword}，目标: {count} 条")
        self._ensure_browser()

        page = self._context.new_page()
        results = []

        try:
            search_url = (
                f"https://www.xiaohongshu.com/search_result"
                f"?keyword={keyword}&source=web_search_result_notes"
            )

            # 先访问首页检查登录状态
            page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=20000)
            time.sleep(2)

            # 快速判断是否需要登录（只看是否跳转到登录页）
            if "/login" in page.url:
                print("  ⚠️ 未登录，请先点击「登录小红书」按钮")
                page.close()
                return []

            # 访问搜索页
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)

            # 先尝试提取——如果能提取到就说明没问题
            results = self._extract_notes_from_page(page, keyword)
            print(f"  首次提取: {len(results)} 条")

            # 如果一条都提取不到，可能是登录问题或页面加载问题
            if len(results) == 0:
                # 截图存下来方便排查
                try:
                    screenshot_dir = os.path.join(os.path.dirname(self.USER_DATA_DIR), "debug")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    page.screenshot(path=os.path.join(screenshot_dir, "search_page.png"))
                    print(f"  已保存截图到 data/debug/search_page.png 供排查")
                except Exception:
                    pass

            # 滚动加载更多
            seen_ids = set(r["note_id"] for r in results)
            last_total = len(results)
            no_change_rounds = 0

            for _ in range(min(count // 10 + 5, 15)):
                if len(results) >= count:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(2.0, 3.5))

                new_results = self._extract_notes_from_page(page, keyword)
                # 合并新结果（去重）
                for item in new_results:
                    if item["note_id"] not in seen_ids:
                        seen_ids.add(item["note_id"])
                        results.append(item)

                if len(results) == last_total:
                    no_change_rounds += 1
                    if no_change_rounds >= 3:
                        break
                else:
                    no_change_rounds = 0
                    print(f"  已获取 {len(results)} 条...")
                    last_total = len(results)

            print(f"  完成，共 {len(results)} 条")

        except Exception as e:
            print(f"  异常: {e}")
        finally:
            page.close()

        return results[:count]

    def _check_need_login(self, page) -> bool:
        """
        检查页面是否需要登录。
        策略：优先检查「已登录」特征，而不是找「登录」文字。
        因为小红书很多页面元素里都有"登录"二字（如"登录后可查看全文"），
        容易误判。
        """
        try:
            current_url = page.url

            # 1. URL 直接跳转到登录页 — 确定需要登录
            if "/login" in current_url or "login.xiaohongshu.com" in current_url:
                print(f"  检测到登录页URL: {current_url}")
                return True

            # 2. 检查是否有「已登录」的标志（用户头像/昵称/消息图标）
            #    如果找到这些，说明已经登录，不需要再登录
            logged_in_indicators = [
                ".user-avatar",          # 用户头像
                ".side-bar-user",        # 侧边栏用户信息
                "[class*='avatar']",     # 头像元素
                ".reds-icon.message",    # 消息图标（登录后才显示）
                ".login-btn",            # 注意：这是「已登录状态」下的按钮（如发布笔记）
            ]

            try:
                # 用 JS 快速判断：页面有没有明显的登录弹窗
                has_login_modal = page.evaluate("""
                    () => {
                        // 检查是否有登录弹窗（通常是最顶层的大弹窗）
                        const modals = document.querySelectorAll(
                            '.login-container, .login-modal, [class*="login"][class*="modal"], ' +
                            '[class*="Login"]'
                        );
                        for (const m of modals) {
                            if (m.offsetParent !== null) return true; // 可见
                        }
                        // 检查是否有 "手机号登录" 这样的大标题（不是导航栏小字）
                        const hElements = document.querySelectorAll('h1, h2, h3, .title, [class*="title"]');
                        for (const h of hElements) {
                            const text = h.textContent.trim();
                            if (text === '登录' || text === '手机号登录' || text === '登录小红书') {
                                const rect = h.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 20) return true;
                            }
                        }
                        return false;
                    }
                """)
                if has_login_modal:
                    print("  检测到登录弹窗（大尺寸登录UI）")
                    return True
            except Exception:
                pass

            # 3. 尝试找笔记内容 — 如果能找到搜索结果/笔记卡片，说明已在正常浏览
            try:
                has_notes = page.evaluate("""
                    () => {
                        const notes = document.querySelectorAll(
                            'section.note-item, .note-item, a[href*="/explore/"], ' +
                            '[class*="feeds"], .search-result, .feeds-page'
                        );
                        return notes.length > 0;
                    }
                """)
                if has_notes:
                    print("  检测到笔记内容 — 已登录")
                    return False
            except Exception:
                pass

            # 4. 兜底：如果页面有大量内容但没检测到笔记，也不报登录
            try:
                body_text = page.evaluate("() => document.body.innerText.length")
                if body_text > 500:
                    # 页面内容充足，可能只是加载慢
                    return False
            except Exception:
                pass

            return False

        except Exception:
            return False

    @staticmethod
    def _parse_count(text: str) -> int:
        """解析 XHS 互动计数（支持 '1.2万', '999', '10万+' 等格式）"""
        if not text:
            return 0
        text = text.strip().replace("+", "").replace(",", "")
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return 0
        try:
            return int(re.sub(r"[^0-9]", "", text) or 0)
        except ValueError:
            return 0

    def _extract_notes_from_page(self, page, keyword: str) -> List[Dict]:
        """
        从当前页面提取笔记数据。

        核心思路：找所有 a[href*="/explore/"] 链接（XHS 固定 URL 结构），
        而非依赖 React 动态 class name。这是唯一不会随 XHS 前端更新而失效的方法。
        """
        notes = []

        # 等待页面渲染（给 JS 一点时间）
        time.sleep(0.5)

        try:
            notes_data = page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();

                    // === 策略：找所有指向 /explore/ 的链接 ===
                    // XHS 笔记卡片一定包含一个指向 /explore/{24位hexID} 的 <a> 标签
                    const allExploreLinks = document.querySelectorAll('a[href*="/explore/"]');

                    allExploreLinks.forEach(link => {
                        try {
                            const href = link.getAttribute('href') || '';
                            // 提取 note_id: /explore/ 后跟 24 位 hex
                            const match = href.match(/\\/explore\\/([a-f0-9]{20,32})/);
                            if (!match) return;
                            const noteId = match[1];
                            if (seen.has(noteId)) return;
                            seen.add(noteId);

                            // === 找到笔记卡片容器 ===
                            // XHS 的卡片结构: 外层容器 > 链接(含封面图) > 底部信息区(标题/作者/点赞)
                            // 向上查找较大的容器（至少包含 img + 文本）
                            let card = link;
                            for (let i = 0; i < 6; i++) {
                                const parent = card.parentElement;
                                if (!parent || parent === document.body) break;
                                // 如果父容器包含多张图片/链接，说明到了外层列表，停在这里
                                const childImgs = parent.querySelectorAll('img').length;
                                const childLinks = parent.querySelectorAll('a[href*="/explore/"]').length;
                                if (childLinks >= 2 || childImgs >= 3) break;
                                card = parent;
                            }

                            // === 提取封面图 ===
                            const img = card.querySelector('img');
                            let coverUrl = '';
                            if (img) {
                                coverUrl = img.src || img.getAttribute('data-src') || img.getAttribute('srcset')?.split(' ')[0] || '';
                                // XHS 图片 URL 通常包含 ci.xiaohongshu.com 或 sximg 域名
                            }

                            // === 提取标题 ===
                            // 卡片中文本最长的 span/div（排除数字计数）
                            let title = '';
                            let maxTextLen = 0;
                            const textNodes = card.querySelectorAll('span, div, p, a');
                            textNodes.forEach(el => {
                                // 跳过 img 的 alt text 和纯数字
                                if (el.children.length > 0) return;
                                const text = el.textContent.trim();
                                if (text.length > 5 && text.length < 200 && text.length > maxTextLen) {
                                    // 排除纯数字/计数文本
                                    if (/^[\\d,.万+]+$/.test(text)) return;
                                    // 排除 "小红书" 品牌名等噪音
                                    if (text === '小红书' || text === 'REDnote') return;
                                    title = text;
                                    maxTextLen = text.length;
                                }
                            });

                            // === 提取作者名 ===
                            // XHS 作者名通常是较短文本（2-12字），在卡片底部区域
                            let authorName = '';
                            const spans = card.querySelectorAll('span');
                            spans.forEach(span => {
                                const text = span.textContent.trim();
                                if (text.length >= 2 && text.length <= 15 &&
                                    !/^[\\d,.万+]+$/.test(text) &&
                                    !text.includes('万') &&
                                    span.children.length === 0) {
                                    // 排除标题本身
                                    if (text !== title && !authorName) {
                                        authorName = text;
                                    }
                                }
                            });

                            // === 提取点赞数 ===
                            let likes = 0;
                            // 在卡片中搜索所有包含 "万" 或纯数字的短文本
                            const allSpans = card.querySelectorAll('span, div');
                            allSpans.forEach(el => {
                                if (el.children.length > 0) return;
                                const text = el.textContent.trim();
                                // 匹配点赞格式: "1.2万", "999", "10万+"
                                if (/^[\\d,.]+万?\\+?$/.test(text) && text.length <= 8) {
                                    // 找最大的数字（通常是点赞数，比其他计数大）
                                    const val = parseFloat(text.replace(/[+万]/g, ''));
                                    const actual = text.includes('万') ? val * 10000 : val;
                                    if (actual > likes) {
                                        likes = Math.round(actual);
                                    }
                                }
                            });

                            // === 提取描述 ===
                            let description = '';
                            // 描述通常在标题之后，是较长的文本
                            const allTextEls = card.querySelectorAll('span, div, p');
                            allTextEls.forEach(el => {
                                if (el.children.length > 0) return;
                                const text = el.textContent.trim();
                                if (text.length > 20 && text.length < 500 &&
                                    text !== title && !description) {
                                    description = text;
                                }
                            });

                            results.push({
                                note_id: noteId,
                                title: title,
                                author_name: authorName,
                                cover_url: coverUrl,
                                likes: likes,
                                description: description,
                                href: href.startsWith('http') ? href : 'https://www.xiaohongshu.com' + href,
                            });
                        } catch(e) {}
                    });

                    return results;
                }
            """)

            # === 处理提取的数据 ===
            now = datetime.now()
            for item in notes_data:
                if not item.get("note_id"):
                    continue

                note_id = item["note_id"]
                title = item.get("title", "").strip()
                author_name = item.get("author_name", "").strip()
                cover_url = item.get("cover_url", "")

                # 使用提取到的点赞数（0 表示未能提取）
                likes = item.get("likes", 0)
                # 不编造互动数据 — 没提取到的就是 0
                collects = 0
                comments = 0
                shares = 0

                if not title:
                    title = f"小红书搜索「{keyword}」笔记"

                if not author_name:
                    author_name = "小红书用户"

                notes.append({
                    "note_id": note_id,
                    "title": title,
                    "description": item.get("description", ""),
                    "author_name": author_name,
                    "author_id": hashlib.md5(note_id.encode()).hexdigest()[:12],
                    "cover_url": cover_url,
                    "video_url": "",
                    "images": [cover_url] if cover_url else [],
                    "likes": likes,
                    "collects": collects,
                    "comments": comments,
                    "shares": shares,
                    "tags": [],
                    "keyword": keyword,
                    "tool_name": None,
                    "project_type": None,
                    "difficulty_level": None,
                    "content_category": None,
                    "source_url": f"https://www.xiaohongshu.com/explore/{note_id}",
                    "source": "real",
                    "is_trending": False,
                    "ai_confidence": 0.0,
                    "publish_time": now.isoformat(),
                })

        except Exception as e:
            print(f"  页面提取异常: {e}")
            import traceback
            traceback.print_exc()

        return notes

    def check_login_status(self) -> Dict:
        """检查登录状态"""
        try:
            self._ensure_browser()
            page = self._context.new_page()
            page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)

            need_login = self._check_need_login(page)
            current_url = page.url
            page.close()

            return {
                "logged_in": not need_login,
                "url": current_url,
                "need_login": need_login,
            }
        except Exception as e:
            return {
                "logged_in": False,
                "error": str(e),
                "need_login": True,
            }
        finally:
            if page:
                page.close()
