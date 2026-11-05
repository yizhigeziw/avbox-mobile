package com.github.avbox.osc.sourcedata

import android.text.TextUtils
import android.util.Base64

import com.github.catvod.crawler.SpiderReaper
import com.github.avbox.osc.R
import com.github.avbox.osc.api.ApiConfig
import com.github.avbox.osc.bean.AbsJson
import com.github.avbox.osc.bean.AbsXml
import com.github.avbox.osc.bean.SourceBean
import com.github.avbox.osc.util.AppContextHolder
import com.github.avbox.osc.util.BoundedCall
import com.github.avbox.osc.util.AppLog
import com.github.avbox.osc.util.LanguageManager
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withTimeoutOrNull

import java.io.UnsupportedEncodingException
import java.net.URLDecoder
import java.util.ArrayList
import java.util.concurrent.Callable

class PushDetailResolver(private val gson: Gson, private val detailResult: SourceChannel<AbsXml?>) {

    suspend fun checkPush(data: AbsXml): AbsXml {
        val videoList = data.movie?.videoList
        if (videoList != null && videoList.size > 0) {
            val video = videoList[0]
            val infoList = video.urlBean?.infoList
            if (infoList != null && infoList.size > 0) {
                for (i in infoList.indices) {
                    val urlinfo = infoList[i]
                    val beanList = urlinfo.beanList
                    if (beanList != null && beanList.isNotEmpty()) {
                        for (infoBean in beanList) {
                            val beanUrl = infoBean.url ?: continue
                            if (beanUrl.startsWith("push://")) {
                                var pushUrl = beanUrl.substring(7)
                                if (pushUrl.startsWith("b64:")) {
                                    try {
                                        pushUrl = String(Base64.decode(pushUrl.substring(4), Base64.DEFAULT or Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8)
                                    } catch (e: UnsupportedEncodingException) {
                                        AppLog.e("SourceViewModel", e)
                                    }
                                } else {
                                    pushUrl = URLDecoder.decode(pushUrl)
                                }

                                val sb = ApiConfig.get().getSource("push_agent")
                                val res = if (sb == null) null else fetchPushDetail(sb, pushUrl)

                                if (res != null) {
                                    val resVideoList = res.movie?.videoList
                                    if (resVideoList != null && resVideoList.size > 0) {
                                        val resVideo = resVideoList[0]
                                        val resInfoList = resVideo.urlBean?.infoList
                                        if (resInfoList != null && resInfoList.size > 0) {
                                            if (beanList.size == 1) {
                                                infoList.removeAt(i)
                                            } else {
                                                beanList.remove(infoBean)
                                            }
                                            for (resUrlinfo in resInfoList) {
                                                val resBeanList = resUrlinfo.beanList
                                                if (resBeanList != null && resBeanList.isNotEmpty()) {
                                                    infoList.add(resUrlinfo)
                                                }
                                            }
                                            video.sourceKey = "push_agent"
                                            return data
                                        }
                                    }
                                }
                                infoBean.name = str(R.string.player_parse_failed_prefix, infoBean.name)
                            }
                        }
                    }
                }
            }
        }
        return data
    }

    private suspend fun fetchPushDetail(sourceBean: SourceBean, pushUrl: String): AbsXml? {
        return try {
            if (sourceBean.type == 4) {
                withTimeoutOrNull(PUSH_DETAIL_TIMEOUT_MS) {
                    val res = SourceHelper.siteGet(sourceBean) {
                        params("ac", "detail")
                        params("ids", pushUrl)
                    }
                    if (TextUtils.isEmpty(res)) null else parsePushDetail(res, sourceBean.key)
                }
            } else {
                val res = BoundedCall.call(Callable<String> {
                    val sp = ApiConfig.get().getCSP(sourceBean)
                    val ids = ArrayList<String>()
                    ids.add(pushUrl)
                    SpiderReaper.track(sp) { sp.detailContent(ids) }
                }, PUSH_DETAIL_TIMEOUT_MS, "echo--push-detail--" + sourceBean.key)
                if (TextUtils.isEmpty(res)) null else parsePushDetail(res, sourceBean.key)
            }
        } catch (e: CancellationException) {
            throw e
        } catch (th: Throwable) {
            AppLog.e("SourceViewModel", th)
            null
        }
    }

    private fun parsePushDetail(res: String?, sourceKey: String?): AbsXml? {
        return try {
            val absJson = gson.fromJson<AbsJson>(res, object : TypeToken<AbsJson>() {}.type)
            val data = absJson.toAbsXml()
            SourceHelper.absXml(data, sourceKey)
            data
        } catch (e: Exception) {
            AppLog.e("SourceViewModel", e)
            null
        }
    }

    companion object {

        private const val PUSH_DETAIL_TIMEOUT_MS = 15_000L

        private fun str(resId: Int, vararg args: Any?): String {
            val context = AppContextHolder.context()
            return if (context == null) "" else LanguageManager.localized(context).getString(resId, *args)
        }
    }
}
