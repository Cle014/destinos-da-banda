from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.views.decorators.http import require_POST
from apps.accommodations.models import TripOrder, TripOrderItem
from .models import GuiaTuristico, Especialidade, AvaliacaoGuia

def guide_list(request):
    qs = GuiaTuristico.objects.filter(activo=True).prefetch_related('especialidades')

    provincia  = request.GET.get('provincia', '')
    idioma     = request.GET.get('idioma', '')
    especialidade = request.GET.get('especialidade', '')
    search     = request.GET.get('q', '')

    if provincia:
        qs = qs.filter(provincia=provincia)
    if idioma:
        qs = qs.filter(idiomas__contains=idioma)
    if especialidade:
        qs = qs.filter(especialidades__slug=especialidade)
    if search:
        qs = qs.filter(
            Q(nome__icontains=search) |
            Q(biografia__icontains=search) |
            Q(municipio__icontains=search)
        )

    total_count = qs.count()

    context = {
        'page_title':    'Guias Turísticos',
        'guides':        qs,
        'total_count':   total_count,
        'provinces':     GuiaTuristico.PROVINCE_CHOICES,
        'idiomas':       GuiaTuristico.IDIOMA_CHOICES,
        'especialidades':Especialidade.objects.all(),
        'filters': {
            'provincia':    provincia,
            'idioma':       idioma,
            'especialidade':especialidade,
            'q':            search,
        },
        'is_filtered': bool(provincia or idioma or especialidade or search),
    }
    return render(request, 'guides/list.html', context)

def guide_detail(request, slug):
    guide = get_object_or_404(GuiaTuristico, slug=slug, activo=True)

    avaliacoes    = guide.avaliacoes.select_related('utilizador').order_by('-data')[:10]
    related       = GuiaTuristico.objects.filter(
        activo=True, provincia=guide.provincia
    ).exclude(pk=guide.pk)[:3]

    user_avaliou  = False
    if request.user.is_authenticated:
        user_avaliou = guide.avaliacoes.filter(utilizador=request.user).exists()

    context = {
        'page_title':  guide.nome,
        'guide':       guide,
        'avaliacoes':  avaliacoes,
        'related':     related,
        'user_avaliou':user_avaliou,
        'range_5':     range(1, 6),
    }
    return render(request, 'guides/detail.html', context)

@require_POST
def guide_avaliar(request, slug):
    """
    Mecanismo de Confiança (Fase 2.5):
    Avaliações só podem ser submetidas mediante o Código de uma Reserva Concluída
    (TripOrder com item 'guide' concluído para este guia).
    """
    guide = get_object_or_404(GuiaTuristico, slug=slug, activo=True)
    booking_ref = request.POST.get('booking_reference', '').strip().upper()
    contact_check = request.POST.get('contact_verify', '').strip().lower()

    if not booking_ref:
        messages.error(request, 'Indique o Código de Reserva Concluída (ex: DB-XXXXXX) para avaliar este guia.')
        return redirect('guides:detail', slug=slug)

    completed_item = TripOrderItem.objects.select_related('order').filter(
        order__reference_code__iexact=booking_ref,
        item_type='guide',
        item_id=guide.pk,
    ).filter(
        Q(status='completed') | Q(order__status='completed')
    ).first()

    if not completed_item:
        messages.error(
            request,
            f"O código '{booking_ref}' não corresponde a uma reserva concluída com o guia {guide.nome}. "
            "Apenas viajantes com reservas concluídas podem publicar avaliações."
        )
        return redirect('guides:detail', slug=slug)

    order = completed_item.order
    if contact_check and (contact_check not in order.guest_email.lower() and contact_check not in order.guest_phone.lower()):
        messages.error(request, 'O email ou telefone informado não coincide com o titular da reserva concluída.')
        return redirect('guides:detail', slug=slug)

    if guide.avaliacoes.filter(booking_reference__iexact=booking_ref).exists():
        messages.info(request, f'A reserva #{booking_ref} já submeteu uma avaliação para este guia.')
        return redirect('guides:detail', slug=slug)

    try:
        scores = {}
        for field in ('classificacao', 'pontualidade', 'simpatia', 'conhecimento', 'organizacao'):
            val = int(request.POST.get(field, 5))
            if not (1 <= val <= 5):
                raise ValidationError(f'Valor fora do intervalo permitido para {field}.')
            scores[field] = val

        comentario = request.POST.get('comentario', '').strip()[:1000]
        avaliacao = AvaliacaoGuia(
            guia=guide,
            utilizador=request.user if request.user.is_authenticated else None,
            booking_reference=order.reference_code,
            reviewer_name=order.guest_name,
            comentario=comentario,
            **scores,
        )
        avaliacao.full_clean()
        avaliacao.save()
        messages.success(request, f'Avaliação verificada da reserva #{order.reference_code} publicada com sucesso!')
    except (ValueError, TypeError, ValidationError):
        messages.error(request, 'Dados de avaliação inválidos. As classificações devem estar entre 1 e 5.')
    except Exception:
        messages.error(request, 'Erro ao submeter a avaliação. Tente novamente.')

    return redirect('guides:detail', slug=slug)
